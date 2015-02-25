from nipype.interfaces.base import CommandLineInputSpec, CommandLine, TraitedSpec, File, BaseInterfaceInputSpec, traits, BaseInterface, isdefined
from nipype.utils.filemanip import fname_presuffix, split_filename
from nipype.interfaces.freesurfer.base import FSCommand, FSTraitedSpec
from nipype.interfaces.matlab import MatlabCommand
import os
from string import Template



def extract_high(surface, rl):
    """Extracting vertices_high and triangles_high from asc file"""
    import numpy as np
    import os
    with open(surface, 'r') as f:
        f.readline()
        nb_vert = f.readline().split(' ')[0]
        read_data = [[np.double(line.rstrip('\n').split()[0]),
                     np.double(line.rstrip('\n').split()[1]),
                     np.double(line.rstrip('\n').split()[2])] for line in f]

    a = np.array(read_data)
    vert_high = a[0:int(nb_vert), 0:3]
    tri_high = a[int(nb_vert):, 0:3]
    np.savetxt(rl + '_vertices_high.txt', vert_high, fmt='%.6f %.6f %.6f')
    tri_high = a[int(nb_vert):, 0:3]
    np.savetxt(rl +'_triangles_high.txt', tri_high, fmt='%d %d %d')

    return (map(os.path.abspath, [rl + '_vertices_high.txt', rl + '_triangles_high.txt']))





def txt2off(vertices, triangles, rl):
    """converting txt files to off file for the remesher function"""
    import numpy as np
    import os

    vert = np.loadtxt(vertices)
    tri = np.loadtxt(triangles)

    with open(rl + '_high.off', 'w') as f: 
        f.write('OFF\n') 
        f.write('{} {} {}\n'.format(int(vert.shape[0]), int(tri.shape[0]), 0)) 

    with open(rl + '_high.off', 'a') as f:
        np.savetxt(f, vert, fmt='%.6f')
        np.savetxt(f, np.hstack([np.ones((tri.shape[0],1))*3, tri]), fmt='%d')
     
    return os.path.abspath(rl + '_high.off')





def off2txt(surface, rl):
    """convert off file back to txt files"""
    import numpy as np
    import os

    surface
    with open(surface) as f:
        f.readline()
        num = f.readline().split(' ')

    vert = np.loadtxt(surface, skiprows=2, usecols=(0,1,2))  
    vert = vert[:int(num[0]), :]
    tri = np.loadtxt(surface, skiprows=int(num[0])+2, usecols=(1,2,3))  

    np.savetxt(rl + '_vertices_low.txt', vert, fmt='%.4f')
    np.savetxt(rl + '_triangles_low.txt', tri, fmt='%d')
    return (map(os.path.abspath, [rl + '_vertices_low.txt', rl + '_triangles_low.txt']))





def correct_region_mapping(region_mapping_not_corrected, vertices, triangles, rl,
                           region_mapping_corr=0.42):
    """correcting region_mapping_not_corrected, saving corected version as rl_region_mapping_low.txt"""
    import os
    import sys
    #region_mapping_corr = float(os.environ['region_mapping_corr'])
    from copy import deepcopy
    import numpy as np
    from collections import Counter

    texture = np.loadtxt(region_mapping_not_corrected)
    vert = np.loadtxt(vertices)
    trian = np.loadtxt(triangles)
    for _ in range(10):
        new_texture = deepcopy(texture)
        labels = np.unique(texture)
        #import pdb; pdb.set_trace()
        for ilab in labels:
            iverts = (np.nonzero(texture==ilab)[0]).tolist()
            if len(iverts)>0:
                for inode in iverts:
                    iall = trian[np.nonzero(trian==inode)[0]].flatten().tolist()
                    ineig = np.unique(filter(lambda x: x!=inode, iall)).astype('int')
                    # import pdb; pdb.set_trace()
                    ivals = np.array(Counter(texture[ineig]).most_common()).astype('int')                
                    if ivals[np.nonzero(ivals[:,0]==ilab), 1].shape[1]==0:
                        new_texture[inode] = Counter(texture[ineig]).most_common(1)[0][0]
                    elif ivals[np.nonzero(ivals[:,0] == ilab), 1][0,0] < region_mapping_corr * len(ineig):
                        new_texture[inode] = Counter(texture[ineig]).most_common(1)[0][0]
        texture = deepcopy(new_texture) 

    np.savetxt(rl + '_region_mapping_low.txt', new_texture)
    return os.path.abspath(rl + '_region_mapping_low.txt')





def reunify_both_regions(rh_region_mapping, lh_region_mapping, rh_vertices, lh_vertices, rh_triangles, lh_triangles):
    """merging right and left hemispheres region_mapping_low, vertices_low and triangles_low files"""
    import os
    import numpy as np
    lh_reg_map = np.loadtxt(lh_region_mapping)
    lh_vert = np.loadtxt(lh_vertices)
    lh_trian = np.loadtxt(lh_triangles)
    rh_reg_map = np.loadtxt(rh_region_mapping)
    rh_vert = np.loadtxt(rh_vertices)
    rh_trian = np.loadtxt(rh_triangles)
    vertices = np.vstack([lh_vert, rh_vert])
    triangles = np.vstack([lh_trian,  rh_trian + lh_vert.shape[0]])
    region_mapping = np.hstack([lh_reg_map, rh_reg_map])
    np.savetxt('region_mapping.txt', region_mapping, fmt='%d', newline=" ")
    np.savetxt('vertices.txt', vertices, fmt='%.2f')
    np.savetxt('triangles.txt', triangles, fmt='%d %d %d')
    return (map(os.path.abspath, ['region_mapping.txt', 'vertices.txt', 'triangles.txt']))





class Aseg2SrfInputSpec(CommandLineInputSpec):
    in_subject_id = File(desc = "Subject FreeSurfer Id",
                         argstr = '-s %d',
                         exists = True,
                         mandatory = True)

class Aseg2SrfOutputSpec(TraitedSpec):
    out_subcortical_surf_list = File(desc = "Output subcortical surfaces", exists = True)

class Aseg2Srf(CommandLine):
    input_spec = Aseg2SrfInputSpec
    output_spec = Aseg2SrfOutputSpec
    _cmd = './aseg2srf' 

    def _gen_subjects_dir(self):
        return os.getcwd()

    def _list_outputs(self):
        if isdefined(self.inputs.subjects_dir):
            subjects_dir = self.inputs.subjects_dir
        else:
            subjects_dir = self._gen_subjects_dir()
        
        outputs = self.output_spec().get()
        outputs['subject_id'] = self.inputs.subject_id
        outputs['subjects_dir'] = subjects_dir
        subject_path = os.path.join(subjects_dir, self.inputs.subject_id)
        label_list = [4, 5, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 26, 28, 43, 44, 46, 47, 49, 50, 51, 52, 53,
                      54, 58, 60, 251, 252, 253, 254, 255]
        outputs['subcortical_surf'] = [os.path.join(subject_path, 'ascii', 'aseg_%d' %i)
                                       for i in  label_list]
        return outputs






### Remesher wrapper (Tested)
class RemesherInputSpec(CommandLineInputSpec):
    in_file = File(desc = "Input surface", 
                   argstr ='%s', 
                   exists = True, 
                   mandatory = True,
                   position = 0)
    out_file = File(desc = "Remeshed surface",
                    argstr ='%s',
                    exists = True,
                    genfile=True,
                    position = 1)

class RemesherOutputSpec(TraitedSpec):
    out_file = File(desc = "Remeshed surface", exists = True)

class Remesher(CommandLine):
    """
    Call remesher command 
    For input rh_high.txt will return output rh_low.txt
    """
    input_spec = RemesherInputSpec
    output_spec = RemesherOutputSpec
    _cmd = "/home/user/scripts3/remesher/cmdremesher/cmdremesher"
    #_cmd = scripts_dir + "/remesher/cmdremesher/cmdremesher"
    def _gen_filename(self, name):
        if name is 'out_file':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        if isdefined(self.inputs.in_file):
            _, name, ext = split_filename(self.inputs.in_file)
            return name[:2] + "_low" + ext 

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = os.path.abspath(self._gen_outfilename())
        return outputs
### End of Remesher wrapper  





### RegionMapping wrapper (tested)
class RegionMappingInputSpect(BaseInterfaceInputSpec):
    rl = traits.Str(mandatory=True,desc=("right or left hemisphere"))
    aparc_annot = File(exists = True, mandatory = True)
    ref_tables = File(exists = True, mandatory = True)
    vertices_low = File(exists = True, mandatory = True)
    triangles_low = File(exists = True, mandatory = True)
    vertices_high = File(exists = True, mandatory = True)

class RegionMappingOutputSpect(TraitedSpec):
    out_file = File(exists = True)

class RegionMapping(BaseInterface):
    """
    Generate a first region_mapping txt file using the region_mapping_2 matlab function  
    """
    input_spec = RegionMappingInputSpect
    output_spec = RegionMappingOutputSpect

    def _run_interface(self, runtime):
        d = dict(rl = self.inputs.rl,
                 vertices_low = self.inputs.vertices_low,
                 triangles_low = self.inputs.triangles_low,
                 vertices_high = self.inputs.vertices_high,
                 ref_tables = self.inputs.ref_tables,
                 aparc_annot = self.inputs.aparc_annot)
        script = Template("""
            rl = '$rl'
            vertices_low = '$vertices_low';
            triangles_low = '$triangles_low';
            vertices_high = '$vertices_high';
            ref_tables = '$ref_tables';
            aparc_annot = '$aparc_annot';
            addpath('/home/user/scripts3');
            region_mapping_2(rl, vertices_low, triangles_low, vertices_high, ref_tables, aparc_annot); 
            quit;
            """).safe_substitute(d)
        ##changes needed for addpath (specific architecture)
        mlab = MatlabCommand(script=script, mfile=True)
        result = mlab.run()
        return result.runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = os.path.abspath(fname_presuffix("",  prefix=self.inputs.rl, suffix='_region_mapping_low_not_corrected.txt'))
        return outputs
### End of RegionMapping wrapper





### check_region_mapping wrapper (tested)
class CheckRegionMappingInputSpect(CommandLineInputSpec):
    vertices_low = File(argstr ='%s', 
                        exists = True, 
                        mandatory = True,
                        position = 0)
    triangles_low = File(argstr ='%s', 
                         exists = True, 
                         mandatory = True,
                         position = 1)
    region_mapping_low = File(argstr ='%s', 
                              exists = True, 
                              mandatory = True,
                              position = 2)

class CheckRegionMappingOutputSpect(TraitedSpec):
    region_mapping_low = File(exists=True)

class CheckRegionMapping(CommandLine):
    input_spec = CheckRegionMappingInputSpect
    output_spec = CheckRegionMappingOutputSpect
    _cmd = 'python /home/user/scripts3/check_region_mapping_2.py'
    #_cmd = Template("""python '$path'/check_region_mapping_2.py""").safe_substitute(path = scripts_dir)
    _terminal_output = 'stream'
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['region_mapping_low'] = self.inputs.region_mapping_low
        return outputs
### End of check_region_mapping wrapper      




### Corrected MRIsConvert class (Tested)
class MRIsConvertInputSpec(FSTraitedSpec):
    """
    Uses Freesurfer's mris_convert to convert surface files to various formats
    """
    annot_file = File(exists=True, argstr="--annot %s",
    desc="input is annotation or gifti label data")

    parcstats_file = File(exists=True, argstr="--parcstats %s",
    desc="infile is name of text file containing label/val pairs")

    label_file = File(exists=True, argstr="--label %s",
    desc="infile is .label file, label is name of this label")

    scalarcurv_file = File(exists=True, argstr="-c %s",
    desc="input is scalar curv overlay file (must still specify surface)")

    functional_file = File(exists=True, argstr="-f %s",
    desc="input is functional time-series or other multi-frame data (must specify surface)")

    labelstats_outfile = File(exists=False, argstr="--labelstats %s",
    desc="outfile is name of gifti file to which label stats will be written")

    patch = traits.Bool(argstr="-p", desc="input is a patch, not a full surface")
    rescale = traits.Bool(argstr="-r", desc="rescale vertex xyz so total area is same as group average")
    normal = traits.Bool(argstr="-n", desc="output is an ascii file where vertex data")
    xyz_ascii = traits.Bool(argstr="-a", desc="Print only surface xyz to ascii file")
    vertex = traits.Bool(argstr="-v", desc="Writes out neighbors of a vertex in each row")

    scale = traits.Float(argstr="-s %.3f", desc="scale vertex xyz by scale")
    dataarray_num = traits.Int(argstr="--da_num %d", desc="if input is gifti, 'num' specifies which data array to use")

    talairachxfm_subjid = traits.String(argstr="-t %s", desc="apply talairach xfm of subject to vertex xyz")
    origname = traits.String(argstr="-o %s", desc="read orig positions")

    in_file = File(exists=True, mandatory=True, position=-2, argstr='%s', desc='File to read/convert')
    out_file = File(argstr='./%s', position=-1, genfile=True, desc='output filename or True to generate one')
    #Not really sure why the ./ is necessary but the module fails without it

    out_datatype = traits.Enum("ico", "tri", "stl", "vtk", "gii", "mgh", "mgz", "asc", mandatory=True,
    desc="These file formats are supported:  ASCII:       .asc" \
    "ICO: .ico, .tri GEO: .geo STL: .stl VTK: .vtk GIFTI: .gii MGH surface-encoded 'volume': .mgh, .mgz")


class MRIsConvertOutputSpec(TraitedSpec):
    """
    Uses Freesurfer's mris_convert to convert surface files to various formats
    """
    converted = File(exists=True, desc='converted output surface')


class MRIsConvert(FSCommand):
    """
    Uses Freesurfer's mris_convert to convert surface files to various formats
    Example
    -------
    >>> import nipype.interfaces.freesurfer as fs
    >>> mris = fs.MRIsConvert()
    >>> mris.inputs.in_file = 'lh.pial'
    >>> mris.inputs.out_datatype = 'gii'
    >>> mris.run() # doctest: +SKIP
    """
    _cmd = 'mris_convert'
    input_spec = MRIsConvertInputSpec
    output_spec = MRIsConvertOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["converted"] = os.path.abspath(self._gen_outfilename())
        return outputs

    def _gen_filename(self, name):
        if name is 'out_file':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        if isdefined(self.inputs.annot_file):
            _, name, ext = split_filename(self.inputs.annot_file)
        elif isdefined(self.inputs.parcstats_file):
            _, name, ext = split_filename(self.inputs.parcstats_file)
        elif isdefined(self.inputs.label_file):
            _, name, ext = split_filename(self.inputs.label_file)
        elif isdefined(self.inputs.scalarcurv_file):
            _, name, ext = split_filename(self.inputs.scalarcurv_file)
        elif isdefined(self.inputs.functional_file):
            _, name, ext = split_filename(self.inputs.functional_file)
        elif isdefined(self.inputs.in_file):
            _, name, ext = split_filename(self.inputs.in_file)

        return name + ext + "_converted." + self.inputs.out_datatype
### End of corrected MRIsConvert class


