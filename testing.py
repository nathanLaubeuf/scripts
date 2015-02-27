import workflows2 as wf2
import nipype.interfaces.io as nio
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu




subj_id_node = pe.Node(interface=niu.IdentityInterface(fields=['in_subject_id']), name='subj_id_node')
subj_id_node.inputs.in_subject_id = "100408"
subcortical_surface = wf2.SubcorticalSurface()

wf = pe.Workflow(name='wf')

wf.connect([
    (subj_id_node, subcortical_surface, [('in_subject_id', 'inputnode.in_subject_id')])])

wf.run()
