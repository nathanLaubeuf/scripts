function out_file = region_mapping_2(rl, vertices_low, triangles_low, vertices_high, ref_table, aparc_annot)

	FREESURFER_HOME = getenv('FREESURFER_HOME')

	if (~isdeployed)
	    addpath([FREESURFER_HOME, '/matlab'])
	end

	corr_right = load(ref_table);
	[v, L, ct] = read_annotation(aparc_annot);
	a = load(vertices_low);
	b = load(triangles_low);
	c = load(vertices_high);

	reg_map = zeros(size(a,1),1);
	not_found = [];
	for i=1:size(a,1)
	    i;
	    [g,e] = min(abs(c(:,1)-a(i,1))+abs(c(:,2)-a(i,2))+abs(c(:,3)-a(i,3)));
	    find_tab = find(corr_right(:,6) == L(e));
	    if isempty(find_tab)
	        not_found = [i, not_found];
	    else
	        reg_map(i) = corr_right(find_tab,5);
	    end
	end
	not_found

	save([rl, '_region_mapping_low_not_corrected.txt'],'reg_map', '-ascii' ); 
end