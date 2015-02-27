import nipype.interfaces.fsl as fsl
import nipype.interfaces.mrtrix as mrt
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.utility as niu
import nipype.interfaces.matlab as mlab
import nipype.pipeline.engine as pe
from nipype.workflows.dmri.fsl.artifacts import ecc_pipeline 
import utility as su 



inputnode.inputs.pial_rh = ""

def Surface(name='surface'):
    """
    Surface workflow
    Generate vertices, triangles and region mapping files 
    """
    inputnode = pe.Node(interface=niu.IdentityInterface(fields=['pial_rh', 'annot_rh', 'ref_tables_rh', 'pial_lh', 'annot_lh', 'ref_tables_lh','rh', 'lh']), name='inputnode')
    inputnode.inputs.rh ='rh'
    inputnode.inputs.lh ='lh'
    inputnode.inputs.pial_rh = "./rh.pial.asc"
    inputnode.inputs.annot_rh = "./"
    inputnode.inputs.ref_tables_rh = "./rh_ref_table.txt"
    inputnode.inputs.pial_lh = "./"
    inputnode.inputs.annot_lh = "./"
    inputnode.inputs.ref_tables_lh = "./lh_ref_table.txt"


    pial2asc = pe.Node(interface=su.MRIsConvert(), name='pial2asc')
    pial2asc.inputs.out_datatype ='asc'
    pial2asc.inputs.normal = True
    extract_high = pe.Node(interface=niu.Function(input_names=['surface', 'rl'],
                                                  output_names=['vertices_high', 'triangles_high'],
                                                  function=su.extract_high), name='extract_high')
    txt2off = pe.Node(interface=niu.Function(input_names=['vertices', 'triangles', 'rl'],
                                             output_names=['out_file'],
                                             function=su.txt2off),name='txt2off')
    remesher = pe.Node(interface=su.Remesher(), name='remesher')
    off2txt = pe.Node(interface=niu.Function(input_names=['surface', 'rl'],
                                             output_names=['vertices_low', 'triangles_low'],
                                             function=su.off2txt), name='off2txt')
    region_mapping = pe.Node(interface=su.RegionMapping(),name='region_mapping')
    correct_region_mapping = pe.Node(interface=niu.Function(input_names=['region_mapping_not_corrected', 'vertices', 'triangles', 'rl', 'region_mapping_corr'], 
                                                            output_names = ['region_mapping_low'],
                                                            function=su.correct_region_mapping),name='correct_region_mapping')
    check_region_mapping = pe.Node(interface=su.CheckRegionMapping(), name='check_region_mapping')
    reunify_both_regions = pe.Node(interface=niu.Function(input_names = ['rh_region_mapping', 'lh_region_mapping', 'rh_vertices', 'lh_vertices', 'rh_triangles', 'lh_triangles'],
                                                          output_names = ['out_files'],
                                                          function = su.reunify_both_regions), name='reunify_both_regions')


    wfrh = pe.Workflow(name='wfrh')
    wfrh.connect([
        (pial2asc, extract_high, [('converted','surface')]),
        (extract_high, txt2off, [('vertices_high','vertices'),
                                 ('triangles_high','triangles')]),
        (extract_high, region_mapping,[('vertices_high','vertices_high')]),
        (txt2off, remesher, [('out_file','in_file')]),
        (remesher, off2txt, [('out_file','surface')]),
        (off2txt, region_mapping, [('vertices_low','vertices_low'),
                                   ('triangles_low','triangles_low')]),
        (off2txt, correct_region_mapping, [('vertices_low','vertices'),
                                           ('triangles_low','triangles')]),
        (off2txt, check_region_mapping, [('vertices_low','vertices_low'),
                                         ('triangles_low','triangles_low')]),
        (region_mapping, correct_region_mapping,[('out_file','region_mapping_not_corrected')]),
        (correct_region_mapping, check_region_mapping, [('region_mapping_low','region_mapping_low')])
        ])

    wflh = wfrh.clone(name='wflh')

    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode, wfrh,[('pial_rh','pial2asc.in_file')]),
        (inputnode, wflh,[('pial_lh','pial2asc.in_file')]),
        (inputnode, wfrh, [('annot_rh', 'region_mapping.aparc_annot'),
                       ('ref_tables_rh','region_mapping.ref_tables'),
                       ('rh','region_mapping.rl')]),
        (inputnode, wflh, [('annot_lh', 'region_mapping.aparc_annot'),
                       ('ref_tables_lh','region_mapping.ref_tables'),
                       ('lh','region_mapping.rl')]),
        (inputnode, wfrh, [('rh','correct_region_mapping.rl')]),
        (inputnode, wflh, [('lh','correct_region_mapping.rl')]),
        (inputnode, wfrh, [('rh','extract_high.rl')]),
        (inputnode, wflh, [('lh','extract_high.rl')]),
        (inputnode, wfrh, [('rh','txt2off.rl')]),
        (inputnode, wflh, [('lh','txt2off.rl')]),
        (inputnode, wfrh,[('rh','off2txt.rl')]),
        (inputnode, wflh,[('lh','off2txt.rl')]),
        (wfrh,reunify_both_regions,[('check_region_mapping.region_mapping_low', 'rh_region_mapping')]),
        (wflh,reunify_both_regions,[('check_region_mapping.region_mapping_low', 'lh_region_mapping')]),
        (wfrh,reunify_both_regions,[('off2txt.vertices_low', 'rh_vertices')]),
        (wflh,reunify_both_regions,[('off2txt.vertices_low', 'lh_vertices')]),
        (wfrh,reunify_both_regions,[('off2txt.triangles_low', 'rh_triangles')]),
        (wflh,reunify_both_regions,[('off2txt.triangles_low', 'lh_triangles')])
        ])
    
    return wf