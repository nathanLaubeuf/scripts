import nipype.interfaces.fsl as fsl
import nipype.interfaces.mrtrix as mrt
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.utility as niu
import nipype.interfaces.matlab as mlab
import nipype.pipeline.engine as pe
from nipype.workflows.dmri.fsl.artifacts import ecc_pipeline 
import utility as su 





def SubcorticalSurface(name='subcortical_surfaces'):
    """ extraction of the subcortical surfaces from FreeSurfer"""
    inputnode = pe.Node(interface=niu.IdentityInterface(fields=['in_subject_id']), name='inputnode')
    aseg2srf = pe.Node(interface=su.Aseg2Srf(), name='aseg2srf')
    list_subcortical = pe.MapNode(interface=su.ListSubcortical(), name='list_subcortical', iterfield=['in_file'])
    #ListSubcortical not in su
    outputnode = pe.MapNode(interface=niu.IdentityInterface(fields=['out_tri_files','out_vert_files']), name='outputnode', iterfield=['out_tri_files','out_vert_files'])

    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode, aseg2srf, [('in_subject_id', 'in_subject_id')]),
        (aseg2srf, list_subcortical, [('out_files', 'in_file')]),
        (list_subcortical, outputnode, [('triangles', 'out_tri_files')]),
        (list_subcortical, outputnode, [('vertices', 'out_vert_files')])
        ])

    return wf