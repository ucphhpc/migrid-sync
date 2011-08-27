function summarize_data_after_time_t(number_of_workers)
% This routine summarizes the results computed on different grid computers
% in
% 1) One value-matrix
% 2) One policy-matrix
% 3) One matrix V_rent needed for time t-1

load value_policy % contains value-matrix, policy-matrix, vectors_of_coordinates, number_states
[value_rent(t,:),policy_rent(t,:,:)]=summarize_results_in_backward_induction(number_of_workers,vectors_of_coordinates,number_states); % HERE ONLY FOR TESTING
t=t-1;
save('value_policy','value_rent','policy_rent','vectors_of_coordinates','number_states','t','number_points_i','number_points_r')
V_rent=reshape(value_rent(t+1,:,:),number_points_i,number_points_r);
save('time_dependent_data','V_rent')


% *** subfunction
function [value,policy] = summarize_results_in_backward_induction(number_of_workers,vectors_of_coordinates,number_states)
value=repmat(NaN,[1 number_states]);
policy=repmat(NaN,[number_states 5]);
% summarize results from Grid
for index_worker=1:number_of_workers
    value_rent_t=dlmread(['value_rent_index_job' num2str(index_worker) '.txt']);
    policy_rent_t=dlmread(['policy_rent_index_job' num2str(index_worker) '.txt']);
    index_set=vectors_of_coordinates{index_worker};
    value(index_set)=value_rent_t;
    policy(index_set,:)=policy_rent_t;
end
disp('Done merging results.')
