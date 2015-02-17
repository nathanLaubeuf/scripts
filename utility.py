from nipype.interfaces.base import CommandLineInputSpec, CommandLine, TraitedSpec, File, BaseInterfaceInputSpec

def extract_high(surface, rl):
    """Extracting vertices and triangles"""
    import numpy as np
    import os
    name_file = rl + surface
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
    """converting txt files to off files for the remesher function"""
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
    """reconvert off file to txt files after remeshing"""
    import numpy as np
    import os

    surface
    with open(surface) as f:
        f.readline()
        num = f.readline().split(' ')

    vert = np.loadtxt(surface, skiprows=2, usecols=(0,1,2))  
    vert = vert[:int(num[0]), :]
    tri = np.loadtxt(surface, skiprows=int(num[0])+2, usecols=(1,2,3))  

    np.savetxt(rl + '_vertices_low.off', vert, fmt='%.4f')
    np.savetxt(rl + '_triangles_low.off', tri, fmt='%d')
    return (map(os.path.abspath, [rl + '_vertices_high.txt', rl + '_triangles_high.txt']))

def correct_region_mapping(region_mapping_not_corrected, vertices, triangles, rl,
                           region_mapping_corr=0.42):
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

def reunify_both_regions(region_mapping_list, vertices_list, triangles_list, rl):
    import os
    import numpy as np
    lh_reg_map = np.loadtxt(region_mapping_list([0]))
    lh_vert = np.loadtxt(vertices_list[0])
    lh_trian = np.loadtxt(triangles_list[0])
    rh_reg_map = np.loadtxt(region_mapping_list[1])
    rh_vert = np.loadtxt(vertices_list[1])
    rh_trian = np.loadtxt(triangles_list[1])
    vertices = np.vstack([lh_vert, rh_vert])
    triangles = np.vstack([lh_trian,  rh_trian + lh_vert.shape[0]])
    region_mapping = np.hstack([lh_reg_map, rh_reg_map])
    np.savetxt('region_mapping.txt', region_mapping, fmt='%d', newline=" ")
    np.savetxt('vertices.txt', vertices, fmt='%.2f')
    np.savetxt('triangles.txt', triangles, fmt='%d %d %d')
    return (map(os.path.abspath(), ['region_mapping.txt', 'vertices.txt', 'triangles.txt']))


class Aseg2SrfInputSpec(CommandLineInputSpec):
    in_subject_id = File(desc = "Subject FreeSurfer Id",
                         argstr = '%d',
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

### Remesher wrapper
class RemesherInputSpec(CommandLineInputSpec):
    in_file = File(desc = "Input surface", 
                   argstr ='%s', 
                   exists = True, 
                   mandatory = True,
                   position = 0)
    out_file = File(desc = "Remeshed surface", 
                    exists = True, 
                    name_source = ['in_file'], 
                    argstr = '%s',
                    position = 1)

class RemesherOutputSpec(TraitedSpec):
    out_file = File(desc = "Remeshed surface", exists = True)

class Remesher(CommandLine):
    input_spec = RemesherInputSpec
    output_spec = RemesherOutputSpec
    _cmd = "./remesher/cmdremesher/cmdremesher"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = os.path.abspath(input_spec.out_file)
        return outputs
### End of Remesher wrapper    

### RegionMapping wrapper
class RegionMappingInputSpect(BaseInterfaceInputSpec):
    rl = File(desc = "right or left hemisphere",
              exists = True,
              mandatory = True)
    aparc_annot = File(exists = True, mandatory = True)
    ref_tables = File(exists = True, mandatory = True)
    vertices_low = File(exists = True, mandatory = True)
    triangles_low = File(exists = True, mandatory = True)
    vertices_high = File(exists = True, mandatory = True)
    out_file = File(rl + '_region_mapping_low.txt', desc ="region_mapping_not_corrected")

class RegionMappingOutputSpect(TraitedSpec):
    out_file = File(exists = True)

class RegionMapping(object):
    input_spec = RegionMappingInputSpect
    output_spec = RegionMappingOutputSpect

    def _run_interface(self, runtime):
        d = dict(rl=self.inputs.rl,
                 vertices_low=self.inputs.vertices_low,
                 triangles_low=self.inputs.triangles_low,
                 vertices_high=self.inputs.vertices_high,
                 ref_tables=self.inputs.ref_tables,
                 aparc_annot=self.inputs.aparc_annot,
                 out_file=self.inputs.out_file)
        #this is your MATLAB code template
        script = Template("""rl = '$rl';
            vertices_low = '$vertices_low';
            triangles_low = '$triangles_low';
            vertices_high = '$vertices_high';
            ref_table = '$ref_table';
            aparc_annot = '$aparc_annot';
            out_file = '$out_file';
            region_mapping_2(rl, vertices_low, triangles_low, vertices_high, ref_table, aparc_annot, out_file); quit;
            """).substitute(d)
        mlab = MatlabCommand(script=script, mfile=True)
        result = mlab.run()
        return result.runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = os.path.abspath(self.inputs.out_file)
        return outputs
### End of RegionMapping wrapper

### check_region_mapping wrapper
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
                              position = 2,
                              name_source = ['vertices_low'])

class CheckRegionMappingOutputSpect(TraitedSpec):
    region_mapping_low = File(exists=True)

class CheckRegionMapping(CommandLine):
    input_spec = CheckRegionMappingInputSpect
    output_spec = CheckRegionMappingOutputSpect
    _cmd = 'python check_region_mapping_2.py'

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['region_mapping_low'] = os.path.abspath(input_spec.out_file)
        return outputs
### End of check_region_mapping wrapper      
