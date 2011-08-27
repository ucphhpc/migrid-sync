function solve_problem_for_one_index_set(index_worker,t)
% called with 4 arguments (from Python code)
% 1) index_worker
% 2) time
% 3) time_independent_data (input argument to make sure that data is sent to grid computer)
% 4) time_dependent_data (input argument to make sure that data is sent to grid computer)

%initialization

try
    t=str2num(t);
end
try
    index_worker=str2num(index_worker);
end


% %%%%%%%% INITIALIZATIONS %%%%%%%%%%%%%%%%
% 
% % SOURCE CODE STILL HAS TO BE OPTIMIZED FOR SPEED
% %clear;  clear workspace
% %clc; % clear command window
% %addpath('subroutines')
% 
% number_of_workers=2;
% 
% % investor preferences
% beta=0.96; % utility discount factor
% gamma=5; % risk-aversion
% phi=0.2; % elasticity of intertemporal substitution
% psi=0.2; % housing preference (0.2 is empirical estimate for fraction spent on housing)
% k=0; % strength of bequest motive
% 
% % life cycle, retirement, eduction, employment
% T=81; % length of investment horizon (81), at age 99 investor makes last decision, at age 100 investor is dead with probability 1
% retirement_age=65; % retirement age
% retirement_income_risky=0; % 1 for "yes", 0 for "no". If retirement_income_risky, retirement income is subject to same vola as during working life, but during retirement mu_log_labor=0
% education=2; % 1 for "no high school", 2 for "high school", 3 for "college"
% income_frac_unemployed=0.0; % fraction of labor income received when investor is unemployed
% prob_get_unemployed_vector=[0.015*ones(retirement_age-21,1); zeros(T-retirement_age+21,1)]; % probability of loosing job when being employed
% prob_get_job_vector=[0.31*ones(retirement_age-21,1); ones(T-retirement_age+21,1)]; % probability of finding job when being unemployed
% 
% % technical stuff
% scaling_factor=10^2; % scaling factor used in objective function for numerical purposes
% parallel_execution=0; % binary variable indicating whether optimization shall be run in parallel (1) or not (0)
% starting_guess=[0.1 0.0 0.7]; % solution numerical optimizer starts with, 1) consumption/wealth, 2) stocks/wealth, 3) housing/wealth
% 
% % housing related constants
% kappa=Inf; % defaulting costs (fraction of home value), "Inf" for no defaulting possible
% maintenance=0.014; % annual maintenance costs for home owner (Harding et al. (2007), also American Housing Survey 2009 (estimated by Bertram))
% fee_sell=0.06; % transaction cost in percent of house value when selling, broker's fee (-0.06, OECD Global Property Guide Studie von 2007)
% minimum_downpayment=0.2; % minimum downpayment as fraction of house value (20% commonly asked for by lender, also YZ 2005)
% 
% % asset characteristics
% rf_log=log(1.02); % risk free rate
% mortgage_rate_log=log(1.04); % mortgage rate
% mu_log_equity=0.0586; % mean return equity, estimate Holger
% sigma_log_equity=0.1672; % standard deviation return on equity, estimate Holger
% mu_log_house=0.0068; % expected return on house, estimate Holger
% sigma_log_house=0.14; % standard deviation return on individual house (not index), Flavin/Yamashita (2002)
% % standard deviation labor is (investor specific) and chosen depending on education
% 
% % correlations
% correlation_house_stock=0.3412; % correlation between return on house and return on stock (0, Flavin/Yamashita (2002))
% correlation_house_labor=0.3101; % correlation between return on house and growth of labor income (0.55, Cocco (2005))
% correlation_stock_labor=0.1350; % correlation between return on stock and growth of labor income (0, Cocco et al. (2005))
% correlation_house_rent=-0.9638; % correlation between return on house and innovation rent price process
% correlation_stock_rent=-0.3021; % correlation between return on stock and innovation rent price process
% correlation_labor_rent=-0.4055; % correlation between growth of labor income and innovation rent price process
% 
% % rent rate process (estimates Holger)
% mean_revsion=0.0702; % mean revesion parameter in rent rate process
% sigma_rent=0.0657; % standard deviation in rent rate process
% mu_rent=-3.117;% mean in rent rate process, NOTE: exp(-3.117)=4.43\% very low, a level of 5% results in reasonable home ownership rates
% %replacement_ratio=0.88983; 
% % END OF INPUT PARAMETERS
% if education==1 % parameters from Cocco et al. (2005) paper
%     replacement_ratio=0.88983; 
%     sigma_log_labor=0.1025;
%     poly_constant=-2.1361;
%     poly_age=0.1684;
%     poly_age2=-0.0353;
%     poly_age3=0.0023;
% elseif education==2
%     replacement_ratio=0.68212; 
%     sigma_log_labor=0.103;
%     poly_constant=-2.1700;
%     poly_age=0.1682;
%     poly_age2=-0.0323;
%     poly_age3=0.0020;
% elseif education==3
%     replacement_ratio=0.938871; 
%     sigma_log_labor=0.13;
%     poly_constant=-4.3148;
%     poly_age=0.3194;
%     poly_age2=-0.0577;
%     poly_age3=0.0033;
% else
%     disp('no assignments.')
%     error('Wrong input for education.')
% end
% % upper and lower bounds
% lb=[0.01 0 0.05]; % 1) consumption/wealth, 2) stocks/wealth, 3) housing/wealth
% ub=[]; % 1) consumption/wealth, 2) stocks/wealth, 3) housing/wealth
% 
% 
% % numerical specification
% options=struct('Display','final','LargeScale','on', ...
%    'TolX',1e-6,'TolFun',1e-6,'TolCon',1e-6,'DerivativeCheck','off',...
%    'Diagnostics','off','FunValCheck','off',...
%    'GradObj','off','GradConstr','off',...
%    'HessMult',[],...% HessMult [] by default
%    'Hessian','off','HessPattern','sparse(ones(numberOfVariables))',...
%    'MaxFunEvals','100*numberOfVariables',...
%    'MaxSQPIter','10*max(numberOfVariables,numberOfInequalities+numberOfBounds)',...
%    'DiffMaxChange',1e-1,'DiffMinChange',1e-8,...
%    'PrecondBandWidth',0,'TypicalX','ones(numberOfVariables,1)',...
%    'MaxPCGIter','max(1,floor(numberOfVariables/2))', ...
%    'TolPCG',0.1,'MaxIter',400,'OutputFcn',[],'PlotFcns',[],...
%    'RelLineSrchBnd',[],'RelLineSrchBndDuration',1,'NoStopIfFlatInfeas','off', ...
%    'PhaseOneTotalScaling','off');
% options=optimset(options,'TolCon',1.e-6,'TolX',1.e-6,'TolFun',1.e-6,'MaxIter',3000,'LargeScale','off','Display','off');
% % TolCon = Toleranz bei Constraints, TolX = Termination Tolerance in Argument, TolFun = termination toerance on function value
% 
% deviation_constraint=10^-5; % make linear constraints a bit harder to avoid that investor does not leave corner solution
% number_points_quadrature=[5 5 5 5]; % 1) stock, 2) house, 3) labor, 4) rent
% number_points_i=5; % number of points for income/wealth in grid
% number_points_r=5; % number of points for level of rent-ratio in grid
% number_points_h=5; % number of points for housing/wealth in grid
% 
% % upper and lower bounds in grid
% h_min=0.1; % minimum value for housing to wealth ratio in grid
% h_max=3; % maximum value for housing to wealth ratio in grid
% i_min=0.01; % minimum value for income to wealth ratio in grid
% i_max=1; % maximum value for income to wealth ratio in grid
% r_min=0.02; % minimum value for rent ratio
% r_max=0.2; % maximum value for rent ratio
% 
% % mortaility table
% sterbew=[ % here: female CSO2001 table
% 0.00048
% 0.00035
% 0.00026
% 0.0002
% 0.00019
% 0.00018
% 0.00018
% 0.00021
% 0.00021
% 0.00021
% 0.00022
% 0.00023
% 0.00027
% 0.0003
% 0.00033
% 0.00035
% 0.00039
% 0.00041
% 0.00043
% 0.00046
% 0.00047
% 0.00048
% 0.0005
% 0.0005
% 0.00052
% 0.00054
% 0.00056
% 0.0006
% 0.00063
% 0.00066
% 0.00068
% 0.00073
% 0.00077
% 0.00082
% 0.00088
% 0.00097
% 0.00103
% 0.00111
% 0.00117
% 0.00123
% 0.0013
% 0.00138
% 0.00148
% 0.00159
% 0.00172
% 0.00187
% 0.00205
% 0.00227
% 0.0025
% 0.00278
% 0.00308
% 0.00341
% 0.00379
% 0.0042
% 0.00463
% 0.0051
% 0.00563
% 0.00619
% 0.0068
% 0.00739
% 0.00801
% 0.00868
% 0.00939
% 0.01014
% 0.01096
% 0.01185
% 0.01282
% 0.01389
% 0.01507
% 0.01636
% 0.01781
% 0.01947
% 0.0213
% 0.0233
% 0.0255
% 0.0279
% 0.03053
% 0.03341
% 0.03658
% 0.04005
% 0.04386
% 0.04911
% 0.05495
% 0.06081
% 0.06727
% 0.07445
% 0.08099
% 0.09079
% 0.10107
% 0.11202
% 0.12192
% 0.12685
% 0.13688
% 0.15164
% 0.17031
% 0.19366
% 0.21566
% 0.23848
% 0.24216
% 0.25523
% 1
% ];
% ueberlebensw=1-sterbew;
% ueberlebensw(20+T)=0;
% clear sterbew
% % END OF INPUT PARAMETERS
% lb12=lb(1:2);
% starting_guess12=starting_guess(1:2);
% 
% if ~isinf(kappa)
%     disp('Note: To run computations with option to default activate code in u_new_owner and u_stay_owner. By default the code is deactivated for performance reasons.')
% end
% 
% phifactor=1-1/phi;
% 
% % span grid for income/wealth, housing/wealth and rent rate
% % points logs of labor/wealth equally distributed
% log_min_i=log(i_min); log_max_i=log(i_max); points_log_i=(log_min_i:(log_max_i-log_min_i)/(number_points_i-1):log_max_i);
% points_i=exp(points_log_i);
% % points logs of rent rate equally distributed
% log_min_r=log(r_min); log_max_r=log(r_max); points_log_r=(log_min_r:(log_max_r-log_min_r)/(number_points_r-1):log_max_r);
% points_r=exp(points_log_r);
% 
% % points housing/wealth equally distributed
% points_h=[h_min h_min+(h_max-h_min)/(number_points_h-1)*(1:(number_points_h-1))];
% 
% % initialize utility from bequest
% if k==0
%     k=eps; % set k to non-zero value to avoid numerical problems
% elseif k<0
%     error('Strength of bequest motive has to be non-negative')
% end
% 
% % initialize data structure for value functions and policies
% value_rent=repmat(NaN,[T number_points_i*number_points_r]);
% policy_rent=repmat(NaN,[T number_points_i*number_points_r 5]);
% 
% max_borrowing=1-minimum_downpayment;
% R=exp(rf_log); % gross risk-free rate
% R_mort=exp(mortgage_rate_log); % gross mortgage rate
% correlation_matrix=[
%     1 correlation_house_stock correlation_stock_rent correlation_stock_labor;
%     correlation_house_stock 1 correlation_house_rent correlation_house_labor;
%     correlation_stock_rent correlation_house_rent 1 correlation_labor_rent;
%     correlation_stock_labor correlation_house_labor correlation_labor_rent 1;
%     ]; % matrix containing correlations between 1) stock, 2) house, 3) rent ratio, 4) labor
% 
% cov_log3=repmat(NaN,[3 3]);
% sigma_log=[sigma_log_equity sigma_log_house sigma_rent];
% for index_i=1:size(sigma_log,2)
%     for index_j=1:size(sigma_log,2)
%         cov_log3(index_i,index_j)=sigma_log(index_i)*sigma_log(index_j)*correlation_matrix(index_i,index_j);
%     end
% end
% cov_log4=repmat(NaN,[4 4]);
% sigma_log=[sigma_log_equity sigma_log_house sigma_rent sigma_log_labor];
% for index_i=1:size(sigma_log,2)
%     for index_j=1:size(sigma_log,2)
%         cov_log4(index_i,index_j)=sigma_log(index_i)*sigma_log(index_j)*correlation_matrix(index_i,index_j);
%     end
% end
% % test if covariance matrix is positive definite (and Cholesky
% % decomposition can be performed)
% chol(cov_log3);
% chol(cov_log4);
% clear sigma_log
% 
% % generate all combinations of gridpoints
% %[log_rown,log_iown,hown]=meshgrid(points_log_r,points_log_i,points_h);
% [log_rrent,log_irent]=meshgrid(points_log_r,points_log_i);
% 
% % Inititialize (terminal condition)
% for index=1:numel(log_rrent)
%     cd=psi^psi*(1-psi)^(1-psi)/exp(log_rrent(index))^psi; % Cobb-Douglas from optimal consumption and house size
%     value_rent(T,index)=k^(1/(1-gamma))*cd;
% end
% 
% % constraint bonds>=-housevalue*(1-minimum_downpayment)in form A*x<=b for
% % renter buying house
% A_buy=[1 1 minimum_downpayment+maintenance];
% b_buy=1-deviation_constraint;
% b_no_sale=1-deviation_constraint;
% A_stay=[1 1];
% 
% %t=T-1; benji edit
% % generate vector of indices (to split problem up in parts for execution on multiple computers)
% rand('state',37);
% random_permutation_indices_problem=randperm(numel(value_rent(1,:,:)));
% minimum_jobs=floor(numel(value_rent(1,:,:))/number_of_workers);
% number_jobs=minimum_jobs*ones(number_of_workers,1)+[ones(numel(value_rent(1,:,:))-minimum_jobs*number_of_workers,1);zeros(number_of_workers-numel(value_rent(1,:,:))+minimum_jobs*number_of_workers,1)];
% cums_number_jobs=cumsum(number_jobs);
% % build structure for indices
% vectors_of_coordinates=cell(number_of_workers,1);
% vectors_of_coordinates{1}=random_permutation_indices_problem(1:cums_number_jobs(1));
% for index=2:number_of_workers
%     vectors_of_coordinates{index}=random_permutation_indices_problem(cums_number_jobs(index-1)+1:cums_number_jobs(index));
% end % for
% 
% number_states=numel(log_rrent);
% V_rent=reshape(value_rent(T,:,:),number_points_i,number_points_r);
% 
% % build data structure "value_policy" that allows saving computed results
% %save('value_policy','value_rent','policy_rent','vectors_of_coordinates','number_states','t','number_points_i','number_points_r')
% % build data structure "time_independent_data" containing data/parameters
% % that are not time dependent
% %save time_independent_data starting_guess12 starting_guess A_stay A_buy b_buy b_no_sale lb12 lb ub options A_buy b_buy b_no_sale A_stay log_rrent log_irent phifactor k beta mean_revsion mu_rent log_min_i log_max_i log_min_r log_max_r R R_mort scaling_factor number_jobs vectors_of_coordinates ueberlebensw prob_get_unemployed_vector prob_get_job_vector retirement_age retirement_income_risky mu_log_equity mu_log_house number_points_quadrature cov_log3 cov_log4 psi vectors_of_coordinates psi gamma
% %save time_dependent_data V_rent
% disp('Initialization finished.')


%%%%%%%% INIT END %%%%%%%%%%%%%%%%%%%%%%%


%load('initialization.m')
load time_independent_data
load time_independent_data psi gamma beta
load time_dependent_data
index_set=vectors_of_coordinates{index_worker};
% compute time dependent data that is not stored in "time_dependent_data"
% was "preparations_for_time_t" in earlier version of the code



age=19+t;
survival_prob=ueberlebensw(age+1);
prob_get_unemployed=prob_get_unemployed_vector(t);
prob_get_employed=prob_get_job_vector(t);
% age dependent drift of labor income as in Cocco et al. (2005)
if age<retirement_age % age dependent drift
    % Fitted to polynomial of order three as in Cocco et al. (2005)
    mu_log_labor=(poly_constant+poly_age*(age+1)+poly_age2*(age+1)^2/10+poly_age3*(age+1)^3/100)-(poly_constant+poly_age*age+poly_age2*age^2/10+poly_age3*age^3/100);
    % Gross returns stocks, house, rent and labor income are jointly lognormally distributed
    mu_log=[mu_log_equity mu_log_house 0 mu_log_labor]; % mean of stochastic component in rent rate process is zero (in process defined via logs)
    [stuetzstellen,wahrsch_stuetzstellen]=qnwlogn(number_points_quadrature,mu_log,cov_log4);
    Gs=stuetzstellen(:,1);
    Gh=stuetzstellen(:,2);
    log_gr=log(stuetzstellen(:,3));
    Gl_employed=stuetzstellen(:,4);
    Gl_unemployed=stuetzstellen(:,4);
elseif retirement_income_risky % drift mu_log_labor 0 but same labor income risk as during working life
    % Fitted to polynomial of order three as in Cocco et al. (2005)
    mu_log_labor=0;
    % Gross returns stocks, house, rent and labor income are jointly lognormally distributed
    mu_log=[mu_log_equity mu_log_house 0 mu_log_labor]; % mean of stochastic component in rent rate process is zero (in process defined via logs)
    [stuetzstellen,wahrsch_stuetzstellen]=qnwlogn(number_points_quadrature,mu_log,cov_log4);
    Gs=stuetzstellen(:,1);
    Gh=stuetzstellen(:,2);
    log_gr=log(stuetzstellen(:,3));
    if age==retirement_age % investor just retired and received last labor income. Next period he receives retirement benefits for the first time
        Gl_employed=replacement_ratio*stuetzstellen(:,4);
        Gl_unemployed=replacement_ratio*stuetzstellen(:,4);
    else
        Gl_employed=stuetzstellen(:,4);
    end
else % drift in labor income deterministic (and equal to inflation rate)
    cov_log=[];
    % Gross returns stocks, house and are jointly lognormally distributed
    mu_log=[mu_log_equity mu_log_house 0]; % mean of stochastic component in rent rate process is zero (in process defined via logs)
    [stuetzstellen,wahrsch_stuetzstellen]=qnwlogn(number_points_quadrature(1:3),mu_log,cov_log3);
    Gs=stuetzstellen(:,1);
    Gh=stuetzstellen(:,2);
    log_gr=log(stuetzstellen(:,3));
    if age==retirement_age % investor just retired and received last labor income. Next period he receives retirement benefits for the first time
        Gl_employed=replacement_ratio*ones(size(stuetzstellen(:,3)));
        Gl_unemployed=replacement_ratio*ones(size(stuetzstellen(:,3)));
    else
        Gl_employed=ones(size(stuetzstellen(:,3)));
    end
end
% end of what was "preparations_for_time_t" in earlier version of the code

value_rent_t=repmat(NaN,numel(index_set),1);
policy_rent_t=repmat(NaN,numel(index_set),5);
for index=1:numel(index_set) 
    % Stategy 1: Stay renter, only choose consumption, housing is multiple of consumption
    multiple_housing=psi/(1-psi)/exp(log_rrent(index));
    % constraint bonds>=0 in form A*x<=b
    A=[1+multiple_housing*exp(log_rrent(index)) 1];
    % optimization
    [policy_w,value_rent_w]=fmincon_mm(@optimize_point,starting_guess12,A,b_no_sale,[],[],lb12,ub,[],options,log_rrent(index),log_irent(index),V_rent,log_rrent,log_irent,Gs,Gl_employed,Gh,psi,gamma,phifactor,k,beta,log_gr,mean_revsion,mu_rent,log_min_i,log_max_i,log_min_r,log_max_r,multiple_housing,survival_prob,R,R_mort,wahrsch_stuetzstellen,scaling_factor);
    % first position is trading strategy, last positions appends house size and bond position
    policy_rent_point=[0 policy_w policy_w(1)*multiple_housing 1-sum(policy_w)-policy_w(1)*multiple_housing*exp(log_rrent(index))]; % bt=1-ct-st-at-ht*lease_rate;
    value_rent_t(index)=-value_rent_w/scaling_factor;
    policy_rent_t(index,:)=policy_rent_point;
end % for
dlmwrite(['value_rent_index_job' num2str(index_worker) '.txt'],value_rent_t)
dlmwrite(['policy_rent_index_job' num2str(index_worker) '.txt'],policy_rent_t)


% *** SUBROUTINE OPTIMIZE_POINT
% this is the objective function that has to be optimized for each and
% every grid point
function utility = optimize_point(decision,log_init_r,log_init_i,V_rent,log_rrent,log_irent,Gs,Gl,Gh,psi,gamma,phifactor,k,beta,log_gr,mean_revsion,mu_rent,log_min_i,log_max_i,log_min_r,log_max_r,multiple_housing,survival_prob,R,R_mort,wahrsch_stuetzstellen,scaling_factor)

ct=decision(1); % consumption-wealth ratio
st=decision(2); % stocks-wealth ratio
ht=ct*multiple_housing; % exploiting optimal relation between consumption and house size

bt=1-ct-ht*exp(log_init_r)-st; % bond holdings
% Growth of total wealth
Wt1_Wt=st*Gs+bt*(R*(bt>=0)+R_mort*(bt<0))+exp(log_init_i)*Gl;
%Wt1_Wt=Wt1_Wt.*(Wt1_Wt>=10^-10)+10^-10.*(Wt1_Wt<10^-10); % only needed for home owner

% log labor-to-wealth ratio for employed investor at time t+1 (it1)
it1=log_init_i+log(Gl./Wt1_Wt);

% log rent rate at time t+1 (rt1)
rt1=log_init_r+mean_revsion*(mu_rent-log_init_r)+log_gr;

% Adjust values that are plugged into interpolating grid in such a way that
% they never leave upper and lower bounds
it1=it1.*(it1>=log_min_i & it1<=log_max_i)+log_min_i.*(it1<log_min_i)+log_max_i.*(it1>log_max_i);
rt1=rt1.*(rt1>=log_min_r & rt1<=log_max_r)+log_min_r.*(rt1<log_min_r)+log_max_r.*(rt1>log_max_r);

vt1em=interp2(log_rrent,log_irent,V_rent,rt1,it1,'*linear');

% Growth factor multiplied to vt1
%growth=kron(ones(2,1),Wt1_Wt./(Gh).^psi);
growth=Wt1_Wt./(Gh).^psi;
%utility_from_bequest=kron(ones(2,1),k*(psi^psi*(1-psi)^(1-psi)./exp(rt1).^psi).^(1-gamma));
utility_from_bequest=k*(psi^psi*(1-psi)^(1-psi)./exp(rt1).^psi).^(1-gamma);

utility=-scaling_factor*(((ct^(1-psi)*ht^psi)^phifactor+beta*wahrsch_stuetzstellen'*((growth.^(1-gamma).*(survival_prob.*(vt1em.^(1-gamma))+(1-survival_prob)*utility_from_bequest))')')^(phifactor/(1-gamma)))^(1/phifactor); % minus at beginning since function shall be maximized and not minimized


function [x,lb,ub,msg] = checkbounds_mm(xin,lbin,ubin,nvars)
%CHECKBOUNDS Verify that the bounds are valid with respect to initial point.
%
% This is a helper function.

%   [X,LB,UB,X,FLAG] = CHECKBOUNDS(X0,LB,UB,nvars) 
%   checks that the upper and lower
%   bounds are valid (LB <= UB) and the same length as X (pad with -inf/inf
%   if necessary); warn if too long.  Also make LB and UB vectors if not 
%   already. Finally, inf in LB or -inf in UB throws an error.

msg = [];
% Turn into column vectors
lb = lbin(:); 
ub = ubin(:); 
xin = xin(:);

lenlb = length(lb);
lenub = length(ub);
lenx = length(xin);

% Check maximum length
if lenlb > nvars
   warning('optimlib:checkbounds:IgnoringExtraLbs', ...
           'Length of lower bounds is > length(x); ignoring extra bounds.');
   lb = lb(1:nvars);   
   lenlb = nvars;
elseif lenlb < nvars
   lb = [lb; -inf*ones(nvars-lenlb,1)];
   lenlb = nvars;
end

if lenub > nvars
   warning('optimlib:checkbounds:IgnoringExtraUbs', ...
           'Length of upper bounds is > length(x); ignoring extra bounds.');
   ub = ub(1:nvars);
   lenub = nvars;
elseif lenub < nvars
   ub = [ub; inf*ones(nvars-lenub,1)];
   lenub = nvars;
end

% Check feasibility of bounds
len = min(lenlb,lenub);
if any( lb( (1:len)' ) > ub( (1:len)' ) )
   count = full(sum(lb>ub));
   if count == 1
      msg=sprintf(['Exiting due to infeasibility:  %i lower bound exceeds the' ...
            ' corresponding upper bound.'],count);
   else
      msg=sprintf(['Exiting due to infeasibility:  %i lower bounds exceed the' ...
            ' corresponding upper bounds.'],count);
   end 
end
% check if -inf in ub or inf in lb   
if any(eq(ub, -inf)) 
   error('optimlib:checkbounds:MinusInfUb', ...
         '-Inf detected in upper bound: upper bounds must be > -Inf.');
elseif any(eq(lb,inf))
   error('optimlib:checkbounds:PlusInfLb', ...
         '+Inf detected in lower bound: lower bounds must be < Inf.');
end

x = xin;
% CKRON Repeated Kronecker products on a cell array of matrices.
% USAGE
%   z=ckron(b)     Solves (B1xB2x...xBd)
%   z=ckron(b,1)   Solves (inv(B1)xinv(B2)x...xinv(Bd))
% where x denotes Kronecker (tensor) product.
% The Bi are passed as a cell array B. 

% Copyright (c) 1997-2000, Paul L. Fackler & Mario J. Miranda
% paul_fackler@ncsu.edu, miranda.4@osu.edu

function z=ckron(b,invert)

if nargin<1, error('At least one parameter must be passed'), end
if nargin==1, invert=0; end

[d,m,n]=csize(b);
if invert & any(m~=n)
  error('Matrix elements must be square to invert');
end

if isempty(d)
  if invert z=inv(b); else z=b; end
else
  if invert z=inv(b{1})
  else z=b{1};
  end
  for i=2:d
    if invert
      z=kron(z,inv(b{i}));
    else
      z=kron(z,b{i});
    end
  end
end

function [SD, dirType] = compdir_mm(Z,H,gf,nvars,f);
% COMPDIR computes a search direction in a subspace defined by Z.  
% [SD,dirType] = compdir(Z,H,gf,nvars,f) returns a search direction for the
% subproblem 0.5*Z'*H*Z + Z'*gf. Helper function for NLCONST. SD is Newton
% direction if possible. SD is a direction of negative curvature if the
% Cholesky factorization of Z'*H*Z fails. If the negative curvature
% direction isn't negative "enough", SD is the steepest descent direction.
% For singular Z'*H*Z, SD is the steepest descent direction even if small,
% or even zero, magnitude.

% Define constant strings
Newton = 'Newton';                     % Z'*H*Z positive definite
NegCurv = 'negative curvature chol';   % Z'*H*Z indefinite
SteepDescent = 'steepest descent';     % Z'*H*Z (nearly) singular

dirType = [];
% Compute the projected Newton direction if possible
projH = Z'*H*Z;
[R, p] = chol(projH);
if ~p  % positive definite: use Newton direction
    %  SD=-Z*((Z'*H*Z)\(Z'*gf));
    % Disable the warnings about conditioning for singular and
    % nearly singular matrices
    warningstate1 = warning('off', 'MATLAB:nearlySingularMatrix');
    warningstate2 = warning('off', 'MATLAB:singularMatrix');
    SD = - Z*(R \ ( R'\(Z'*gf)));
    % Restore the warning states to their original settings
    warning(warningstate1)
    warning(warningstate2)
    dirType = Newton;
else % not positive definite
    [L,sneg] = choltrap(projH);
    if ~isempty(sneg) & sneg'*projH*sneg < -sqrt(eps) % if negative enough
        SD = Z*sneg;
        dirType = NegCurv;
    else % Not positive definite, not negative definite "enough",
        % so use steepest descent direction
        stpDesc = - Z*(Z'*gf);
        % ||SD|| may be (close to) zero, but qpsub handles that case
        SD = stpDesc;
        dirType = SteepDescent;
    end %   
end % ~p  (positive definite)

% Make sure it is a descent direction
if gf'*SD > 0
    SD = -SD;
end

%-----------------------------------------------
function [L,sneg] = choltrap(A)
% CHOLTRAP Compute Cholesky factor or direction of negative curvature.
%     [L, SNEG] = CHOLTRAP(A) computes the Cholesky factor L, such that
%     L*L'= A, if it exists, or returns a direction of negative curvature
%     SNEG for matrix A when A is not positive definite. If A is positive
%     definite, SNEG will be []. 
%
%     If A is singular, it is possible that SNEG will not be a direction of
%     negative curvature (but will be nonempty). In particular, if A is
%     positive semi-definite, SNEG will be nonempty but not a direction of
%     negative curvature. If A is indefinite but singular, SNEG may or may
%     not be a direction of negative curvature.

sneg = [];
n = size(A,1);
L = eye(n);
tol = 0;    % Dividing by sqrt of small number isn't a problem 
for k=1:n-1
    if A(k,k) <= tol
        elem = zeros(length(A),1); 
        elem(k,1) = 1;
        % Disable the warnings about conditioning for singular and
        % nearly singular matrices
        warningstate1 = warning('off', 'MATLAB:nearlySingularMatrix');
        warningstate2 = warning('off', 'MATLAB:singularMatrix');
        sneg = L' \ elem;
        % Restore the warning states to their original settings
        warning(warningstate1)
        warning(warningstate2)
        return;
    else
        L(k,k) = sqrt(A(k,k));
        s = k+1:n;
        L(s,k) = A(s,k)/L(k,k);
        A(k+1:n,k+1:n) =  A(k+1:n,k+1:n)  - tril(L(k+1:n,k)*L(k+1:n,k)');   
    end
end
if A(n,n) <= tol
    elem = zeros(length(A),1); 
    elem(n,1) = 1;
    % Disable the warnings about conditioning for singular and
    % nearly singular matrices
    warningstate1 = warning('off', 'MATLAB:nearlySingularMatrix');
    warningstate2 = warning('off', 'MATLAB:singularMatrix');
    sneg = L' \ elem;
    % Restore the warning states to their original settings
    warning(warningstate1)
    warning(warningstate2)
else
    L(n,n) = sqrt(A(n,n));
end

% CSIZE Returns dimension information for cell arrays.
% USAGE
%   d=csize(b);
%   [d,n]=csize(b);
% If b is a cell array then:
%   d is the number of matrices in b
%   m is a dx2 matrix of row and column dimensions
%     or m and n are dx1 vectors
% If b is not a cell array
%   d=[]; this can be used to test if b is a cell array 
%         (isempty(d) is true is b is not a cell array)
%   m=size(b) or m=size(b,1) and n=size(b,2)

% Copyright (c) 1997-2000, Paul L. Fackler & Mario J. Miranda
% paul_fackler@ncsu.edu, miranda.4@osu.edu

function [d,m,n]=csize(b)

if iscell(b)
  d=length(b);
  m=zeros(d,2);
  for i=1:d
    m(i,:)=size(b{i});
  end
else
  d=[];
  m=size(b);
end

if nargout==0
  disp([(1:d)' m])
elseif nargout==3
  n=m(:,2);
  m=m(:,1);
end

function [gradf,cJac,NEWLAMBDA,OLDLAMBDA,s] = finitedifferences_mm(xCurrent,...
             xOriginalShape,funfcn,confcn,lb,ub,fCurrent,cCurrent,XDATA,YDATA,...
             DiffMinChange,DiffMaxChange,typicalx,finDiffType,variables,...
             LAMBDA,NEWLAMBDA,OLDLAMBDA,POINT,FLAG,s,isFseminf,varargin)
%FINITEDIFFERENCES computes finite-difference derivatives.
%
% This helper function computes finite-difference derivatives of the objective 
% and constraint functions.
%
%  [gradf,cJac,NEWLAMBDA,OLDLAMBDA,s] = FINITEDIFFERENCES(xCurrent, ... 
%                  xOriginalShape,funfcn,confcn,lb,ub,fCurrent,cCurrent, ...
%                  XDATA,YDATA,DiffMinChange,DiffMaxChange,typicalx,finDiffType, ...
%                  variables,LAMBDA,NEWLAMBDA,OLDLAMBDA,POINT,FLAG,s, ...
%                  varargin)
% computes the finite-difference gradients of the objective and
% constraint functions.
%
%  gradf = FINITEDIFFERENCES(xCurrent,xOriginalShape,funfcn,[],lb,ub,fCurrent,...
%                  [],YDATA,DiffMinChange,DiffMaxChange,typicalx,finDiffType,...
%                  variables,[],[],[],[],[],[],varargin)
% computes the finite-difference gradients of the objective function.
%
%
% INPUT:
% xCurrent              Point where gradient is desired
% xOriginalShape        Shape of the vector of variables supplied by the user
%                       (The value of xOriginalShape is NOT used)
% funfcn, confcn        Cell arrays containing info about objective and
%                       constraints, respectively. The objective (constraint) 
%                       derivatives are computed if and only if funfcn 
%                       (confcn) is nonempty.
%                       
% lb, ub                Lower and upper bounds
% fCurrent, cCurrent    Values at xCurrent of the function and the constraints 
%                       to be differentiated. Note that fCurrent can be a scalar 
%                       or a (row or column) vector. 
%
% XDATA, YDATA          Data passed from lsqcurvefit.
%
% DiffMinChange, 
% DiffMaxChange         Minimum and maximum values of perturbation of xCurrent 
% finDiffType           Type of finite difference desired (only forward 
%                       differences implemented so far)
% variables             Variables w.r.t which we want to differentiate. Possible 
%                       values are 'all' or an integer between 1 and the
%                       number of variables.
%
% LAMBDA,NEWLAMBDA,
% OLDLAMBDA,POINT,
% FLAG,s                Parameters for semi-infinite constraints
%
% isFseminf             True if caller is fseminf, false otherwise
%
% varargin              Problem-dependent parameters passed to the objective and 
%                       constraint functions
%
% OUTPUT:
% gradf                 If fCurrent is a scalar, gradf is the finite-difference 
%                       gradient of the objective; if fCurrent is a vector,
%                       gradf is the finite-difference Jacobian  
% cJac                  Finite-difference Jacobian of the constraints
% NEWLAMBDA,
% OLDLAMBDA,s           Parameters for semi-infinite constraints

% For vector-valued functions in funfcn, we make the function values 
% (both at xCurrent and those at the perturbed points) column vectors 
% to ensure that the given fCurrent and the computed fplus will have the 
% same shape so that fplus - fCurrent be well defined.  
fCurrent = fCurrent(:);
numberOfFunctions = numel(fCurrent);
numberOfVariables = numel(xCurrent); 
functionIsScalar = (numberOfFunctions == 1);

% nonEmptyLowerBounds = true if lb is not empty, false if it's empty;
% analogoulsy for nonEmptyUpperBound
nonEmptyLowerBounds = ~isempty(lb);
nonEmptyUpperBounds = ~isempty(ub);

% Make sure xCurrent and typicalx are column vectors so that the 
% operation max(abs(xCurrent),abs(typicalx)) won't error
xCurrent = xCurrent(:); typicalx = typicalx(:);
% Value of stepsize suggested in Trust Region Methods, Conn-Gould-Toint, section 8.4.3
CHG = sqrt(eps)*sign(xCurrent).*max(abs(xCurrent),abs(typicalx));
%
% Make sure step size lies within DiffminChange and DiffMaxChange
%
CHG = sign(CHG+eps).*min(max(abs(CHG),DiffMinChange),DiffMaxChange);
len_cCurrent = length(cCurrent); % For semi-infinite

if nargout < 3
   NEWLAMBDA=[]; OLDLAMBDA=[]; s=[];
end
if nargout > 1
      cJac = zeros(len_cCurrent,numberOfVariables);  
else
      cJac = [];
end
% allVariables = true/false if finite-differencing wrt to all/one variables
allVariables = false;
if ischar(variables)
   if strcmp(variables,'all')
      variables = 1:numberOfVariables;
      allVariables = true;
   else
      error('optimlib:finitedifferences:InvalidVariables', ...
            'Unknown value of input ''variables''.')
   end
end

% Preallocate gradf for speed 
if ~isempty(funfcn)
    if functionIsScalar
        gradf = zeros(numberOfVariables,1);
    elseif allVariables % vector-function and gradf estimates full Jacobian
        gradf = zeros(numberOfFunctions,numberOfVariables);
    else % vector-function and gradf estimates one column of Jacobian
        gradf = zeros(numberOfFunctions,1);
    end
else
    gradf = [];
end

% Do this switch outside of loop for speed
if isFseminf
   vararginAdjusted = varargin(3:end);
else
   vararginAdjusted = varargin;     
end

% If lsqcurvefit, then add XDATA to objective's input list.
% xargin{1} will be updated right before each evaluation 
if ~isempty(XDATA)
    xargin = {xOriginalShape,XDATA};
else
    xargin = {xOriginalShape};
end

for gcnt=variables
   if gcnt == numberOfVariables, 
      FLAG = -1; 
   end
   temp = xCurrent(gcnt);
   xCurrent(gcnt)= temp + CHG(gcnt);
         
   if (nonEmptyLowerBounds && isfinite(lb(gcnt))) || (nonEmptyUpperBounds && isfinite(ub(gcnt)))
      % Enforce bounds while finite-differencing.
      % Need lb(gcnt) ~= ub(gcnt), and lb(gcnt) <= temp <= ub(gcnt) to enforce bounds.
      % (If the last qpsub problem was 'infeasible', the bounds could be currently violated.)
      if (lb(gcnt) ~= ub(gcnt)) && (temp >= lb(gcnt)) && (temp <= ub(gcnt)) 
          if  ((xCurrent(gcnt) > ub(gcnt)) || (xCurrent(gcnt) < lb(gcnt))) % outside bound ?
              CHG(gcnt) = -CHG(gcnt);
              xCurrent(gcnt)= temp + CHG(gcnt);
              if (xCurrent(gcnt) > ub(gcnt)) || (xCurrent(gcnt) < lb(gcnt)) % outside other bound ?
                  [newchg,indsign] = max([temp-lb(gcnt), ub(gcnt)-temp]);  % largest distance to bound
                  if newchg >= DiffMinChange
                      CHG(gcnt) = ((-1)^indsign)*newchg;  % make sure sign is correct
                      xCurrent(gcnt)= temp + CHG(gcnt);

                      % This warning should only be active if the user doesn't supply gradients;
                      % it shouldn't be active if we're doing derivative check 
                      warning('optimlib:finitedifferences:StepReduced', ...
                             ['Derivative finite-differencing step was artificially reduced to be within\n', ...
                              'bound constraints. This may adversely affect convergence. Increasing distance between\n', ...
                              'bound constraints, in dimension %d to be at least %0.5g may improve results.'], ...
                              gcnt,abs(2*CHG(gcnt)))
                  else
                      error('optimlib:finitedifferences:DistanceTooSmall', ...
                          ['Distance between lower and upper bounds, in dimension %d is too small to compute\n', ...
                           'finite-difference approximation of derivative. Increase distance between these\n', ...
                           'bounds to be at least %0.5g.'],gcnt,2*DiffMinChange)
                  end          
              end
          end
      end
   end % of 'if isfinite(lb(gcnt)) || isfinite(ub(gcnt))'
   
   xOriginalShape(:) = xCurrent;
   xargin{1} = xOriginalShape; % update x in list of input arguments to objective
   if ~isempty(funfcn) % Objective gradient required
       % The length of varargin (depending on the caller being fseminf or not)
       % was calculated outside of the loop for speed.
       fplus = feval(funfcn{3},xargin{:},vararginAdjusted{:});
   else
       fplus = [];
   end
   % YDATA: Only used by lsqcurvefit, which has no nonlinear constraints
   % (the only type of constraints we do finite differences on: bounds 
   % and linear constraints do not require finite differences) and thus 
   % no needed after evaluation of constraints
   if ~isempty(YDATA)    
      fplus = fplus - YDATA;
   end
   % Make sure it's in column form
   fplus = fplus(:);
   if ~isempty(funfcn)
       if functionIsScalar
           gradf(gcnt,1) =  (fplus-fCurrent)/CHG(gcnt);
       elseif allVariables % vector-function and gradf estimates full Jacobian
           gradf(:,gcnt) = (fplus-fCurrent)/CHG(gcnt);
       else % vector-function and gradf estimates only one column of Jacobian
           gradf = (fplus-fCurrent)/CHG(gcnt);
       end
   end
   
   if ~isempty(cJac) % Constraint gradient required
         if isFseminf 
            [ctmp,ceqtmp,NPOINT,NEWLAMBDA,OLDLAMBDA,LOLD,s] = ...
               semicon(xOriginalShape,LAMBDA,NEWLAMBDA,OLDLAMBDA,POINT,FLAG,s,varargin{:});            
         else
            [ctmp,ceqtmp] = feval(confcn{3},xOriginalShape,varargin{:});
         end
         cplus = [ceqtmp(:); ctmp(:)];

      % Next line used for problems with varying number of constraints
      if isFseminf && len_cCurrent~=length(cplus)
         cplus=v2sort(cCurrent,cplus); 
      end      
      if ~isempty(cplus)
         cJac(:,gcnt) = (cplus - cCurrent)/CHG(gcnt); 
      end           
   end
    xCurrent(gcnt) = temp;
end % for 








function [X,FVAL,EXITFLAG,OUTPUT,LAMBDA,GRAD,HESSIAN] = fmincon_mm(FUN,X,A,B,Aeq,Beq,LB,UB,NONLCON,options,varargin)
%FMINCON finds a constrained minimum of a function of several variables.
%   FMINCON attempts to solve problems of the form:
%       min F(X)  subject to:  A*X  <= B, Aeq*X  = Beq  (linear constraints)
%        X                     C(X) <= 0, Ceq(X) = 0    (nonlinear constraints)
%                              LB <= X <= UB            (bounds)
%                                                           
%   X=FMINCON(FUN,X0,A,B) starts at X0 and finds a minimum X to the function 
%   FUN, subject to the linear inequalities A*X <= B. FUN accepts input X and 
%   returns a scalar function value F evaluated at X. X0 may be a scalar,
%   vector, or matrix. 
%
%   X=FMINCON(FUN,X0,A,B,Aeq,Beq) minimizes FUN subject to the linear equalities
%   Aeq*X = Beq as well as A*X <= B. (Set A=[] and B=[] if no inequalities exist.)
%
%   X=FMINCON(FUN,X0,A,B,Aeq,Beq,LB,UB) defines a set of lower and upper
%   bounds on the design variables, X, so that a solution is found in 
%   the range LB <= X <= UB. Use empty matrices for LB and UB
%   if no bounds exist. Set LB(i) = -Inf if X(i) is unbounded below; 
%   set UB(i) = Inf if X(i) is unbounded above.
%
%   X=FMINCON(FUN,X0,A,B,Aeq,Beq,LB,UB,NONLCON) subjects the minimization to the 
%   constraints defined in NONLCON. The function NONLCON accepts X and returns 
%   the vectors C and Ceq, representing the nonlinear inequalities and equalities 
%   respectively. FMINCON minimizes FUN such that C(X)<=0 and Ceq(X)=0. 
%   (Set LB=[] and/or UB=[] if no bounds exist.)
%
%   X=FMINCON(FUN,X0,A,B,Aeq,Beq,LB,UB,NONLCON,OPTIONS) minimizes with the 
%   default optimization parameters replaced by values in the structure
%   OPTIONS, an argument created with the OPTIMSET function. See OPTIMSET
%   for details. Used options are Display, TolX, TolFun, TolCon,
%   DerivativeCheck, Diagnostics, FunValCheck, GradObj, GradConstr,
%   Hessian, MaxFunEvals, MaxIter, DiffMinChange and DiffMaxChange,
%   LargeScale, MaxPCGIter, PrecondBandWidth, TolPCG, TypicalX, Hessian,
%   HessMult, HessPattern, PlotFcns, and OutputFcn. Use the GradObj option 
%   to specify that FUN also returns a second output argument G that is the 
%   partial derivatives of the function df/dX, at the point X. Use the Hessian
%   option to specify that FUN also returns a third output argument H that
%   is the 2nd partial derivatives of the function (the Hessian) at the
%   point X. The Hessian is only used by the large-scale method, not the
%   line-search method. Use the GradConstr option to specify that NONLCON
%   also returns third and fourth output arguments GC and GCeq, where GC is
%   the partial derivatives of the constraint vector of inequalities C, and
%   GCeq is the partial derivatives of the constraint vector of equalities
%   Ceq. Use OPTIONS = [] as a  place holder if no options are set.
%  
%   X=FMINCON(PROBLEM) finds the minimum for PROBLEM. PROBLEM is a
%   structure with the function FUN in PROBLEM.objective, the start point
%   in PROBLEM.x0, the linear inequality constraints in PROBLEM.Aineq
%   and PROBLEM.bineq, the linear equality constraints in PROBLEM.Aeq and
%   PROBLEM.beq, the lower bounds in PROBLEM.lb, the upper bounds in 
%   PROBLEM.ub, the nonlinear constraint function in PROBLEM.nonlcon, the
%   options structure in PROBLEM.options, and solver name 'fmincon' in
%   PROBLEM.solver. Use this syntax to solve at the command line a problem 
%   exported from OPTIMTOOL. The structure PROBLEM must have all the fields.
%
%   [X,FVAL]=FMINCON(FUN,X0,...) returns the value of the objective 
%   function FUN at the solution X.
%
%   [X,FVAL,EXITFLAG]=FMINCON(FUN,X0,...) returns an EXITFLAG that describes the 
%   exit condition of FMINCON. Possible values of EXITFLAG and the corresponding 
%   exit conditions are listed below.
%
%   Both medium- and large-scale:
%     1  First order optimality conditions satisfied to the specified tolerance.
%     0  Maximum number of function evaluations or iterations reached.
%    -1  Optimization terminated by the output function.
%   Large-scale only: 
%     2  Change in X less than the specified tolerance.
%     3  Change in the objective function value less than the specified tolerance.
%   Medium-scale only:
%     4  Magnitude of search direction smaller than the specified tolerance and 
%         constraint violation less than options.TolCon.
%     5  Magnitude of directional derivative less than the specified tolerance
%         and constraint violation less than options.TolCon.
%    -2  No feasible point found.
%
%   [X,FVAL,EXITFLAG,OUTPUT]=FMINCON(FUN,X0,...) returns a structure OUTPUT with 
%   the number of iterations taken in OUTPUT.iterations, the number of function
%   evaluations in OUTPUT.funcCount, the norm of the final step in OUTPUT.stepsize, 
%   the algorithm used in OUTPUT.algorithm, the first-order optimality in 
%   OUTPUT.firstorderopt, and the  exit message in OUTPUT.message. The medium scale 
%   algorithm returns the final line search steplength in OUTPUT.lssteplength, and 
%   the large scale algorithm returns the number of CG iterations in OUTPUT.cgiterations.
%
%   [X,FVAL,EXITFLAG,OUTPUT,LAMBDA]=FMINCON(FUN,X0,...) returns the Lagrange multipliers
%   at the solution X: LAMBDA.lower for LB, LAMBDA.upper for UB, LAMBDA.ineqlin is
%   for the linear inequalities, LAMBDA.eqlin is for the linear equalities,
%   LAMBDA.ineqnonlin is for the nonlinear inequalities, and LAMBDA.eqnonlin
%   is for the nonlinear equalities.
%
%   [X,FVAL,EXITFLAG,OUTPUT,LAMBDA,GRAD]=FMINCON(FUN,X0,...) returns the value of 
%   the gradient of FUN at the solution X.
%
%   [X,FVAL,EXITFLAG,OUTPUT,LAMBDA,GRAD,HESSIAN]=FMINCON(FUN,X0,...) returns the 
%   value of the HESSIAN of FUN at the solution X.
%
%   Examples
%     FUN can be specified using @:
%        X = fmincon(@humps,...)
%     In this case, F = humps(X) returns the scalar function value F of the HUMPS function
%     evaluated at X.
%
%     FUN can also be an anonymous function:
%        X = fmincon(@(x) 3*sin(x(1))+exp(x(2)),[1;1],[],[],[],[],[0 0])
%     returns X = [0;0].
%
%   If FUN or NONLCON are parameterized, you can use anonymous functions to capture 
%   the problem-dependent parameters. Suppose you want to minimize the objective
%   given in the function myfun, subject to the nonlinear constraint mycon, where 
%   these two functions are parameterized by their second argument a1 and a2, respectively.
%   Here myfun and mycon are M-file functions such as
%
%        function f = myfun(x,a1)
%        f = x(1)^2 + a1*x(2)^2;
%
%   and
%
%        function [c,ceq] = mycon(x,a2)
%        c = a2/x(1) - x(2);
%        ceq = [];
%
%   To optimize for specific values of a1 and a2, first assign the values to these
%   two parameters. Then create two one-argument anonymous functions that capture 
%   the values of a1 and a2, and call myfun and mycon with two arguments. Finally, 
%   pass these anonymous functions to FMINCON:
%
%        a1 = 2; a2 = 1.5; % define parameters first
%        options = optimset('LargeScale','off'); % run medium-scale algorithm
%        x = fmincon(@(x)myfun(x,a1),[1;2],[],[],[],[],[],[],@(x)mycon(x,a2),options)
%
%   See also OPTIMSET, FMINUNC, FMINBND, FMINSEARCH, @, FUNCTION_HANDLE.

defaultopt = struct('Display','final','LargeScale','on', ...
   'TolX',1e-6,'TolFun',1e-6,'TolCon',1e-6,'DerivativeCheck','off',...
   'Diagnostics','off','FunValCheck','off',...
   'GradObj','off','GradConstr','off',...
   'HessMult',[],...% HessMult [] by default
   'Hessian','off','HessPattern','sparse(ones(numberOfVariables))',...
   'MaxFunEvals','100*numberOfVariables',...
   'MaxSQPIter','10*max(numberOfVariables,numberOfInequalities+numberOfBounds)',...
   'DiffMaxChange',1e-1,'DiffMinChange',1e-8,...
   'PrecondBandWidth',0,'TypicalX','ones(numberOfVariables,1)',...
   'MaxPCGIter','max(1,floor(numberOfVariables/2))', ...
   'TolPCG',0.1,'MaxIter',400,'OutputFcn',[],'PlotFcns',[],...
   'RelLineSrchBnd',[],'RelLineSrchBndDuration',1,'NoStopIfFlatInfeas','off', ...
   'PhaseOneTotalScaling','off');
% If just 'defaults' passed in, return the default options in X
if nargin==1 && nargout <= 1 && isequal(FUN,'defaults')
   X = defaultopt;
   return
end

large = 'large-scale';
medium = 'medium-scale'; 

if nargin < 10, options=[];
   if nargin < 9, NONLCON=[];
      if nargin < 8, UB = [];
         if nargin < 7, LB = [];
            if nargin < 6, Beq=[];
               if nargin < 5, Aeq =[];
               end, end, end, end, end, end

problemInput = false;
if nargin == 1
    if isa(FUN,'struct')
        problemInput = true;
        [FUN,X,A,B,Aeq,Beq,LB,UB,NONLCON,options] = separateOptimStruct(FUN);
    else % Single input and non-structure.
        error('optim:fmincon:InputArg','The input to FMINCON should be either a structure with valid fields or consist of at least four arguments.' );
    end
end

if nargin < 4 && ~problemInput
  error('optim:fmincon:AtLeastFourInputs','FMINCON requires at least four input arguments.')
end

if isempty(NONLCON) && isempty(A) && isempty(Aeq) && isempty(UB) && isempty(LB)
   error('optim:fmincon:ConstrainedProblemsOnly', ...
         'FMINCON is for constrained problems. Use FMINUNC for unconstrained problems.')
end

% Check for non-double inputs
% SUPERIORFLOAT errors when superior input is neither single nor double;
% We use try-catch to override SUPERIORFLOAT's error message when input
% data type is integer.
try
    dataType = superiorfloat(X,A,B,Aeq,Beq,LB,UB);
    if ~isequal('double', dataType)
        error('optim:fmincon:NonDoubleInput', ...
            'FMINCON only accepts inputs of data type double.')
    end
catch
    error('optim:fmincon:NonDoubleInput', ...
        'FMINCON only accepts inputs of data type double.')
end

if nargout > 4
   computeLambda = 1;
else 
   computeLambda = 0;
end

caller='constr';
lenVarIn = length(varargin);
XOUT=X(:);
numberOfVariables=length(XOUT);
%check for empty X
if numberOfVariables == 0
   error('optim:fmincon:EmptyX','You must provide a non-empty starting point.');
end

switch optimget(options,'Display',defaultopt,'fast')
case {'off','none'}
   verbosity = 0;
case 'notify'
   verbosity = 1;  
case 'final'
   verbosity = 2;
case 'iter'
   verbosity = 3;   
otherwise
   verbosity = 2;
end

% Set to column vectors
B = B(:);
Beq = Beq(:);

% Find out what algorithm user wants to run: 
% line_search = false means large scale (trust region), line_search = 1 means medium scale (line search)
line_search = strcmp(optimget(options,'LargeScale',defaultopt,'fast'),'off'); 

[XOUT,l,u,msg] = checkbounds_mm(XOUT,LB,UB,numberOfVariables);
if ~isempty(msg)
   EXITFLAG = -2;
   [FVAL,LAMBDA,GRAD,HESSIAN] = deal([]);
   
   % Create fields in the order they're created in either the medium
   % or large scale algorithms
   OUTPUT.iterations = 0;
   OUTPUT.funcCount = 0;
   OUTPUT.stepsize = [];
   if line_search
      OUTPUT.lssteplength = [];
   end
   if line_search
      OUTPUT.algorithm = 'medium-scale: SQP, Quasi-Newton, line-search';
   else
      OUTPUT.algorithm = 'large-scale: trust-region reflective Newton';
   end
   OUTPUT.firstorderopt = [];
   if ~line_search
      OUTPUT.cgiterations = []; 
   end
   OUTPUT.message = msg;
   
   X(:)=XOUT;
   if verbosity > 0
      disp(msg)
   end
   return
end
lFinite = l(~isinf(l));
uFinite = u(~isinf(u));


meritFunctionType = 0;
mtxmpy = optimget(options,'HessMult',defaultopt,'fast');
if isequal(mtxmpy,'hmult')
   warning('optim:fmincon:HessMultNameClash', ...
           ['Potential function name clash with a Toolbox helper function:\n',...
            ' Use a name besides ''hmult'' for your HessMult function to\n',...
            '  avoid errors or unexpected results.']);
end

diagnostics = isequal(optimget(options,'Diagnostics',defaultopt,'fast'),'on');
funValCheck = strcmp(optimget(options,'FunValCheck',defaultopt,'fast'),'on');
gradflag = strcmp(optimget(options,'GradObj',defaultopt,'fast'),'on');
hessflag = strcmp(optimget(options,'Hessian',defaultopt,'fast'),'on');
if isempty(NONLCON)
   constflag = 0;
else
   constflag = 1;
end

% Convert to inline function as needed
if ~isempty(FUN)  % will detect empty string, empty matrix, empty cell array
   [funfcn, msg] = optimfcnchk_mm(FUN,'fmincon',length(varargin),funValCheck,gradflag,hessflag);
else
   error('optim:fmincon:InvalidFUN', ...
         ['FUN must be a function handle;\n', ...
          ' or, FUN may be a cell array that contains function handles.']);
end

if constflag % NONLCON is non-empty
   gradconstflag = strcmp(optimget(options,'GradConstr',defaultopt,'fast'),'on');
   [confcn, msg] = optimfcnchk(NONLCON,'fmincon',length(varargin),funValCheck,gradconstflag,false,1);
else
   gradconstflag = false; 
   confcn{1} = '';
end

[rowAeq,colAeq]=size(Aeq);
% if only l and u then call sfminbx
if ~line_search && isempty(NONLCON) && isempty(A) && isempty(Aeq) && gradflag
   OUTPUT.algorithm = large;
% if only Aeq beq and Aeq has more columns than rows, then call sfminle
elseif ~line_search && isempty(NONLCON) && isempty(A) && isempty(lFinite) && isempty(uFinite) && gradflag ...
      && colAeq > rowAeq
   OUTPUT.algorithm = large;
elseif ~line_search
   warning('optim:fmincon:SwitchingToMediumScale', ...
   ['Large-scale (trust region) method does not currently solve this type of problem,\n' ...
    ' using medium-scale (line search) instead.'])
   if isequal(funfcn{1},'fungradhess')
      funfcn{1}='fungrad';
      warning('optim:fmincon:HessianIgnored', ...
         ['Medium-scale method is a Quasi-Newton method and does not use\n' ...
         'analytic Hessian. Hessian flag in options will be ignored.'])
   elseif  isequal(funfcn{1},'fun_then_grad_then_hess')
      funfcn{1}='fun_then_grad';
      warning('optim:fmincon:HessianIgnored', ...
         ['Medium-scale method is a Quasi-Newton method and does not use\n' ...
         'analytic Hessian. Hessian flag in options will be ignored.'])
   end    
   hessflag = 0;
   OUTPUT.algorithm = medium;
elseif line_search
   OUTPUT.algorithm = medium;
   if issparse(Aeq) || issparse(A)
      warning('optim:fmincon:ConvertingToFull', ...
              'Cannot use sparse matrices with medium-scale method: converting to full.')
   end
   if line_search && hessflag % conflicting options
      hessflag = 0;
      warning('optim:fmincon:HessianIgnored', ...
         ['Medium-scale method is a Quasi-Newton method and does not use analytic Hessian.\n' ...
         'Hessian flag in options will be ignored (user-supplied Hessian will not be used).']);      
      if isequal(funfcn{1},'fungradhess')
         funfcn{1}='fungrad';
      elseif  isequal(funfcn{1},'fun_then_grad_then_hess')
         funfcn{1}='fun_then_grad';
      end    
   end
   % else call nlconst
else
   error('optim:fmincon:InvalidOptions', ...
      'Unrecognized combination of OPTIONS flags and calling sequence.')
end


lenvlb=length(l);
lenvub=length(u);

if isequal(OUTPUT.algorithm,medium)
   %
   % Ensure starting point lies within bounds
   %
   i=1:lenvlb;
   lindex = XOUT(i)<l(i);
   if any(lindex),
      XOUT(lindex)=l(lindex)+1e-4; 
   end
   i=1:lenvub;
   uindex = XOUT(i)>u(i);
   if any(uindex)
      XOUT(uindex)=u(uindex);
   end
   X(:) = XOUT;
else
   %
   % If initial x not within bounds, set it a to a "box-centered" point
   %
   arg = (u >= 1e10); arg2 = (l <= -1e10);
   u(arg) = inf;
   l(arg2) = -inf;
   if min(min(u-XOUT),min(XOUT-l)) < 0, 
      XOUT = startx(u,l);
      X(:) = XOUT;
   end
end

% Evaluate function
GRAD=zeros(numberOfVariables,1);
HESS = [];

switch funfcn{1}
case 'fun'
   try
      f = feval(funfcn{3},X,varargin{:});
   catch
     error('optim:fmincon:ObjectiveError', ...
            ['FMINCON cannot continue because user supplied objective function' ...
             ' failed with the following error:\n%s'], lasterr)
   end
case 'fungrad'
   try
      [f,GRAD(:)] = feval(funfcn{3},X,varargin{:});
   catch 
      error('optim:fmincon:ObjectiveError', ...
           ['FMINCON cannot continue because user supplied objective function' ...
            ' failed with the following error:\n%s'], lasterr)
   end
case 'fungradhess'
   try
      [f,GRAD(:),HESS] = feval(funfcn{3},X,varargin{:});
   catch
     error('optim:fmincon:ObjectiveError', ...
            ['FMINCON cannot continue because user supplied objective function' ...
             ' failed with the following error:\n%s'], lasterr)
   end
case 'fun_then_grad'
   try
      f = feval(funfcn{3},X,varargin{:});
   catch
     error('optim:fmincon:ObjectiveError', ...
            ['FMINCON cannot continue because user supplied objective function' ...
             ' failed with the following error:\n%s'], lasterr)
   end
   try
      GRAD(:) = feval(funfcn{4},X,varargin{:});
   catch
      error('optim:fmincon:GradError', ...
            ['FMINCON cannot continue because user supplied objective gradient function' ...
             ' failed with the following error:\n%s'], lasterr)
   end
case 'fun_then_grad_then_hess'
   try
      f = feval(funfcn{3},X,varargin{:});
   catch
      error('optim:fmincon:ObjectiveError', ...
            ['FMINCON cannot continue because user supplied objective function' ...
             ' failed with the following error:\n%s'], lasterr)
   end
   try
      GRAD(:) = feval(funfcn{4},X,varargin{:});
   catch
      error('optim:fmincon:GradientError', ...
            ['FMINCON cannot continue because user supplied objective gradient function' ...
             ' failed with the following error:\n%s'], lasterr)     
   end
   try
      HESS = feval(funfcn{5},X,varargin{:});
   catch 
      error('optim:fmincon:HessianError', ...
            ['FMINCON cannot continue because user supplied objective Hessian function' ...
             ' failed with the following error:\n%s'], lasterr)     
   end
otherwise
   error('optim:fmincon:UndefinedCallType','Undefined calltype in FMINCON.');
end

% Check that the objective value is a scalar
if numel(f) ~= 1
   error('optim:fmincon:NonScalarObj','User supplied objective function must return a scalar value.')
end

% Evaluate constraints
switch confcn{1}
case 'fun'
   try 
      [ctmp,ceqtmp] = feval(confcn{3},X,varargin{:});
      c = ctmp(:); ceq = ceqtmp(:);
      cGRAD = zeros(numberOfVariables,length(c));
      ceqGRAD = zeros(numberOfVariables,length(ceq));
   catch
      if findstr(xlate('Too many output arguments'),lasterr)
          if isa(confcn{3},'inline')
              error('optim:fmincon:InvalidInlineNonlcon', ...
                ['The inline function %s representing the constraints\n' ...
                 ' must return two outputs: the nonlinear inequality constraints and\n' ...
                 ' the nonlinear equality constraints.  At this time, inline objects may\n' ...
                 ' only return one output argument: use an M-file function instead.'], ...
                    formula(confcn{3}))            
          elseif isa(confcn{3},'function_handle')
              error('optim:fmincon:InvalidHandleNonlcon', ...
                   ['The constraint function %s must return two outputs:\n' ...
                    ' the nonlinear inequality constraints and\n' ...
                    ' the nonlinear equality constraints.'],func2str(confcn{3}))            
          else
              error('optim:fmincon:InvalidFunctionNonlcon', ...
                   ['The constraint function %s must return two outputs:\n' ...
                    ' the nonlinear inequality constraints and\n' ...
                    ' the nonlinear equality constraints.'],confcn{3})
          end
      else
        error('optim:fmincon:NonlconError', ... 
            ['FMINCON cannot continue because user supplied nonlinear constraint function\n' ...
            ' failed with the following error:\n%s'],lasterr)        
      end
   end
   
case 'fungrad'
   try
      [ctmp,ceqtmp,cGRAD,ceqGRAD] = feval(confcn{3},X,varargin{:});
      c = ctmp(:); ceq = ceqtmp(:);
   catch
      error('optim:fmincon:NonlconError', ... 
           ['FMINCON cannot continue because user supplied nonlinear constraint function\n' ...
            ' failed with the following error:\n%s'],lasterr)  
   end
case 'fun_then_grad'
   try
      [ctmp,ceqtmp] = feval(confcn{3},X,varargin{:});
      c = ctmp(:); ceq = ceqtmp(:);
      [cGRAD,ceqGRAD] = feval(confcn{4},X,varargin{:});
   catch
      error('optim:fmincon:NonlconFunOrGradError', ... 
           ['FMINCON cannot continue because user supplied nonlinear constraint function\n' ...
            'or nonlinear constraint gradient function failed with the following error:\n%s'],lasterr) 
   end
case ''
   c=[]; ceq =[];
   cGRAD = zeros(numberOfVariables,length(c));
   ceqGRAD = zeros(numberOfVariables,length(ceq));
otherwise
   error('optim:fmincon:UndefinedCalltype','Undefined calltype in FMINCON.');
end

non_eq = length(ceq);
non_ineq = length(c);
[lin_eq,Aeqcol] = size(Aeq);
[lin_ineq,Acol] = size(A);
[cgrow, cgcol]= size(cGRAD);
[ceqgrow, ceqgcol]= size(ceqGRAD);

eq = non_eq + lin_eq;
ineq = non_ineq + lin_ineq;

if ~isempty(Aeq) && Aeqcol ~= numberOfVariables
   error('optim:fmincon:WrongNumberOfColumnsInAeq','Aeq has the wrong number of columns.')
end
if ~isempty(A) && Acol ~= numberOfVariables
   error('optim:fmincon:WrongNumberOfColumnsInA','A has the wrong number of columns.')
end
if  cgrow~=numberOfVariables && cgcol~=non_ineq
   error('optim:fmincon:WrongSizeGradNonlinIneq', ...
         'Gradient of the nonlinear inequality constraints is the wrong size.')
end
if ceqgrow~=numberOfVariables && ceqgcol~=non_eq
   error('optim:fmincon:WrongSizeGradNonlinEq', ...
         'Gradient of the nonlinear equality constraints is the wrong size.')
end

if diagnostics > 0
   % Do diagnostics on information so far
   msg = diagnose('fmincon',OUTPUT,gradflag,hessflag,constflag,gradconstflag,...
      line_search,options,defaultopt,XOUT,non_eq,...
      non_ineq,lin_eq,lin_ineq,l,u,funfcn,confcn,f,GRAD,HESS,c,ceq,cGRAD,ceqGRAD);
end


% call algorithm
if isequal(OUTPUT.algorithm,medium)
   [X,FVAL,lambda,EXITFLAG,OUTPUT,GRAD,HESSIAN]=...
      nlconst_mm(funfcn,X,l,u,full(A),B,full(Aeq),Beq,confcn,options,defaultopt, ...
      verbosity,gradflag,gradconstflag,hessflag,meritFunctionType,...
      f,GRAD,HESS,c,ceq,cGRAD,ceqGRAD,varargin{:});
   LAMBDA=lambda;
   
   
else
   if (isequal(funfcn{1}, 'fun_then_grad_then_hess') || isequal(funfcn{1}, 'fungradhess'))
      Hstr=[];
   elseif (isequal(funfcn{1}, 'fun_then_grad') || isequal(funfcn{1}, 'fungrad'))
      n = length(XOUT); 
      Hstr = optimget(options,'HessPattern',defaultopt,'fast');
      if ischar(Hstr) 
         if isequal(lower(Hstr),'sparse(ones(numberofvariables))')
            Hstr = sparse(ones(n));
         else
            error('optim:fmincon:InvalidHessPattern', ...
                  'Option ''HessPattern'' must be a matrix if not the default.')
         end
      end
   end
   
   if isempty(Aeq)
      [X,FVAL,LAMBDA,EXITFLAG,OUTPUT,GRAD,HESSIAN] = ...
         sfminbx(funfcn,X,l,u,verbosity,options,defaultopt,computeLambda,f,GRAD,HESS,Hstr,varargin{:});
   else
      [X,FVAL,LAMBDA,EXITFLAG,OUTPUT,GRAD,HESSIAN] = ...
         sfminle(funfcn,X,sparse(Aeq),Beq,verbosity,options,defaultopt,computeLambda,f,GRAD,HESS,Hstr,varargin{:});
   end
end

% GRIDMAKE Forms grid points
% USAGE
%   X=gridmake(x);
%   X=gridmake(x1,x2,x3,...);
%   [X1,X2,...]=gridmake(x1,x2,x3,...);
%   X=gridmake({y11,y12},x2,{y21,y22,y23});
%
% Expands matrices into the associated grid points.
% If N is the dx2 matrix that indexes the size of the inputs
%   GRIDMAKE returns a prod(N(:,1)) by sum(N(:,2)) matrix.
%   The output can also be returned as either
%      d matrices or 
%      sum(N(:,2)) matices
% If any of the inputs are grids, they are expanded internally
% Thus
%    X=gridmake({x1,x2,x3})
%    X=gridmake(x1,x2,x3)
% and
%    x={x1,x2,x3}; X=gridmake(x{:})
% all produce the same output.
%
% Note: the grid is expanded so the first variable change most quickly.
%
% Example:
%  X=gridmake([1;2;3],[4;5])
% produces
%     1     4
%     2     4
%     3     4
%     1     5
%     2     5
%     3     5
% 
% The function performs an action similar to NDGRID, the main difference is in the
%   increased flexability in specifying the form of the inputs and outputs.
%
% Also the inputs need not be vectors.
%   X=gridmake([1;2;3],[4 6;5 7])
% produces
%     1     4     6
%     2     4     6
%     3     4     6
%     1     5     7
%     2     5     7
%     3     5     7
% 
% See also: ndgrid

% Copyright (c) 1997-2000, Paul L. Fackler & Mario J. Miranda
% paul_fackler@ncsu.edu, miranda.4@osu.edu

function varargout=gridmake(varargin)
m=prod(size(varargin));
n=nargout;
Z=[];
d=zeros(1,m+1);
for i=1:m
  if isa(varargin{i},'cell')
    Z=gridmake2(Z,gridmake(varargin{i}{:}));
  else
    Z=gridmake2(Z,varargin{i});
  end
  d(i+1)=size(Z,2);
end

varargout=cell(1,max(n,1));
if n<=1
  varargout{1}=Z;
elseif n==m
  for i=1:m
    varargout{i}=Z(:,d(i)+1:d(i+1));
  end
elseif n==size(Z,2)
  for i=1:n
    varargout{i}=Z(:,i);
  end
else
  error(['An improper number of outputs requested - should be 1, ' num2str(m)  ' or ' num2str(size(Z,2))])
end

% Expands gridpoints for 2 matrices
function Z=gridmake2(X1,X2)
if isempty(X1); Z=X2; return; end
m=size(X1,1);
n=size(X2,1);
ind1=(1:m)';
ind2=1:n;
Z=[X1(ind1(:,ones(n,1)),:) X2(ind2(ones(m,1),:),:)];function vi = interp3_lok(varargin)
% Fast linear interpolation, X1,X2,X3 have to be passed as generated by MESHGRID
% Routine is called without specifying method!

x=varargin{1};
y=varargin{2};
z=varargin{3};
v=varargin{4};
xi=varargin{5};
yi=varargin{6};
zi=varargin{7};

%{
% this part is only needed if data is not equally spaced
  xx = x(1,:,1).'; yy = y(:,1,1); zz = squeeze(z(1,1,:)); % columns
  dx = diff(xx); dy = diff(yy); dz = diff(zz);
  xdiff = max(abs(diff(dx))); if isempty(xdiff), xdiff = 0; end
  ydiff = max(abs(diff(dy))); if isempty(ydiff), ydiff = 0; end
  zdiff = max(abs(diff(dz))); if isempty(zdiff), zdiff = 0; end
  if (xdiff > eps*max(xx)) || (ydiff > eps*max(yy)) || (zdiff > eps*max(zz))
    if any(dx < 0), % Flip orientation of data so x is increasing.
      x = flipdim(x,2); y = flipdim(y,2); 
      z = flipdim(z,2); v = flipdim(v,2);
      xx = flipud(xx); dx = -flipud(dx);
    end
    if any(dy < 0), % Flip orientation of data so y is increasing.
      x = flipdim(x,1); y = flipdim(y,1);
      z = flipdim(z,1); v = flipdim(v,1);
      yy = flipud(yy); dy = -flipud(dy);
    end
    if any(dz < 0), % Flip orientation of data so y is increasing.
      x = flipdim(x,3); y = flipdim(y,3);
      z = flipdim(z,3); v = flipdim(v,3);
      zz = flipud(zz); dz = -flipud(dz);
    end
  
  end
%}




  [nrows,ncols,npages] = size(v);
  mx = numel(x); my = numel(y); mz = numel(z);
  s = 1 + (xi-x(1))/(x(mx)-x(1))*(ncols-1);
  t = 1 + (yi-y(1))/(y(my)-y(1))*(nrows-1);
  w = 1 + (zi-z(1))/(z(mz)-z(1))*(npages-1);
  
%{
% Check for out of range values of s and set to 1
sout = find((s<1)|(s>ncols));
if ~isempty(sout), s(sout) = ones(size(sout)); end

% Check for out of range values of t and set to 1
tout = find((t<1)|(t>nrows));
if ~isempty(tout), t(tout) = ones(size(tout)); end

% Check for out of range values of w and set to 1
wout = find((w<1)|(w>npages));
if ~isempty(wout), w(wout) = ones(size(wout)); end
%}

% Matrix element indexing, find linear index of element in Matrix v that is
% lower bound in all dimensions
nw = nrows*ncols;
ndx = floor(t)+floor(s-1)*nrows+floor(w-1)*nw;


% Compute intepolation parameters, check for boundary value.
%if isempty(s),
%    d = s;
%else
    d = find(s==ncols);
%end
s(:) = (s - floor(s));
if ~isempty(d),
    s(d) = s(d)+1;
    ndx(d) = ndx(d)-nrows;
end

% Compute intepolation parameters, check for boundary value.
%if isempty(t),
%    d = t;
%else
    d = find(t==nrows);
%end
t(:) = (t - floor(t));
if ~isempty(d),
    t(d) = t(d)+1;
    ndx(d) = ndx(d)-1;
end

% Compute intepolation parameters, check for boundary value.
%if isempty(w),
%    d = w;
%else
    d = find(w==npages);
%end
w(:) = (w - floor(w));
if ~isempty(d),
    w(d) = w(d)+1;
    ndx(d) = ndx(d)-nw;
end


% Now interpolate.
  vi =  (( v(ndx).*(1-t) + v(ndx+1).*t ).*(1-s) + ...
        ( v(ndx+nrows).*(1-t) + v(ndx+(nrows+1)).*t ).*s).*(1-w) +...
       (( v(ndx+nw).*(1-t) + v(ndx+1+nw).*t ).*(1-s) + ...
        ( v(ndx+nrows+nw).*(1-t) + v(ndx+(nrows+1+nw)).*t ).*s).*w;
function [x,FVAL,lambda_out,EXITFLAG,OUTPUT,GRADIENT,HESS]= ...
    nlconst_mm(funfcn,x,lb,ub,Ain,Bin,Aeq,Beq,confcn,OPTIONS,defaultopt,...
    verbosity,gradflag,gradconstflag,hessflag,meritFunctionType,...
    fval,gval,Hval,ncineqval,nceqval,gncval,gnceqval,varargin)
%NLCONST Helper function to find the constrained minimum of a function 
%   of several variables. Called by FMINCON, FGOALATTAIN, FSEMINF, and 
%   FMINIMAX.

% Initialize some parameters
FVAL = []; lambda_out = []; OUTPUT = []; lambdaNLP = []; GRADIENT = []; 
caller = funfcn{2};

% Handle the output
if isfield(OPTIONS,'OutputFcn')
    outputfcn = optimget(OPTIONS,'OutputFcn',defaultopt,'fast');
else
    outputfcn = defaultopt.OutputFcn;
end
if isempty(outputfcn)
  haveoutputfcn = false;
else
  haveoutputfcn = true;
  % Parse OutputFcn which is needed to support cell array syntax
  outputfcn = createCellArrayOfFunctions(outputfcn,'OutputFcn');
end
stop = false;

% Handle the plot functions
if isfield(OPTIONS,'PlotFcns')
    plotfcns = optimget(OPTIONS,'PlotFcns',defaultopt,'fast');
else
    plotfcns = defaultopt.PlotFcns;
end
if isempty(plotfcns)
  haveplotfcn = false;
else
  haveplotfcn = true;
  % Parse PlotFcns which is needed to support cell array syntax
  plotfcns = createCellArrayOfFunctions(plotfcns,'PlotFcns');
end

isFseminf = strcmp(caller,'fseminf');
if haveoutputfcn || haveplotfcn
    [vararginOutputfcn,xOutputfcn] = getArgsForOutputAndPlotFcns(x,caller,varargin{:});
end

iter = 0;
XOUT = x(:);
% numberOfVariables must be the name of this variable
numberOfVariables = length(XOUT);
SD = ones(numberOfVariables,1); 
Nlconst = 'nlconst';
bestf = Inf; 

% Make sure that constraints are consistent Ain,Bin,Aeq,Beq
% Only row consistentcy check. Column check is done in the caller function
if ~isempty(Aeq) && ~isequal(size(Aeq,1),length(Beq))
        error('optim:nlconst:AeqAndBeqInconsistent', ...
            'Row dimension of Aeq is inconsistent with length of beq.')
end
if ~isempty(Ain) && ~isequal(size(Ain,1),length(Bin))
        error('optim:nlconst:AinAndBinInconsistent', ...
            'Row dimension of A is inconsistent with length of b.')
end

if isempty(confcn{1})
    constflag = 0;
else
    constflag = 1;
end
steplength = 1;
HESS=eye(numberOfVariables,numberOfVariables); % initial Hessian approximation.
done = false; 
EXITFLAG = 1;

% Get options
tolX = optimget(OPTIONS,'TolX',defaultopt,'fast');
tolFun = optimget(OPTIONS,'TolFun',defaultopt,'fast');
tolCon = optimget(OPTIONS,'TolCon',defaultopt,'fast');
DiffMinChange = optimget(OPTIONS,'DiffMinChange',defaultopt,'fast');
DiffMaxChange = optimget(OPTIONS,'DiffMaxChange',defaultopt,'fast');
if DiffMinChange >= DiffMaxChange
    error('optim:nlconst:DiffChangesInconsistent', ...
         ['DiffMinChange options parameter is %0.5g, and DiffMaxChange is %0.5g.\n' ...
          'DiffMinChange must be strictly less than DiffMaxChange.'], ...
           DiffMinChange,DiffMaxChange)  
end
DerivativeCheck = strcmp(optimget(OPTIONS,'DerivativeCheck',defaultopt,'fast'),'on');
typicalx = optimget(OPTIONS,'TypicalX',defaultopt,'fast') ;
if ischar(typicalx)
   if isequal(lower(typicalx),'ones(numberofvariables,1)')
      typicalx = ones(numberOfVariables,1);
   else
      error('optim:nlconst:InvalidTypicalX', ...
            'Option ''TypicalX'' must be a numeric value if not the default.')
   end
end
typicalx = typicalx(:); % turn to column vector
maxFunEvals = optimget(OPTIONS,'MaxFunEvals',defaultopt,'fast');
maxIter = optimget(OPTIONS,'MaxIter',defaultopt,'fast');
relLineSrchBnd = optimget(OPTIONS,'RelLineSrchBnd',defaultopt,'fast');
relLineSrchBndDuration = optimget(OPTIONS,'RelLineSrchBndDuration',defaultopt,'fast');
hasBoundOnStep = ~isempty(relLineSrchBnd) && isfinite(relLineSrchBnd) && ...
    relLineSrchBndDuration > 0;
noStopIfFlatInfeas = strcmp(optimget(OPTIONS,'NoStopIfFlatInfeas',defaultopt,'fast'),'on');
phaseOneTotalScaling = strcmp(optimget(OPTIONS,'PhaseOneTotalScaling',defaultopt,'fast'),'on');

% In case the defaults were gathered from calling: optimset('fmincon'):
if ischar(maxFunEvals)
    if isequal(lower(maxFunEvals),'100*numberofvariables')
        maxFunEvals = 100*numberOfVariables;
    else
        error('optim:nlconst:InvalidMaxFunEvals', ...
              'Option ''MaxFunEvals'' must be an integer value if not the default.')
    end
end

% Handle bounds as linear constraints
arglb = ~isinf(lb);
lenlb=length(lb); % maybe less than numberOfVariables due to old code
argub = ~isinf(ub);
lenub=length(ub);
boundmatrix = eye(max(lenub,lenlb),numberOfVariables);
if nnz(arglb) > 0     
    lbmatrix = -boundmatrix(arglb,1:numberOfVariables);% select non-Inf bounds 
    lbrhs = -lb(arglb);
else
    lbmatrix = []; lbrhs = [];
end
if nnz(argub) > 0
    ubmatrix = boundmatrix(argub,1:numberOfVariables);
    ubrhs=ub(argub);
else
    ubmatrix = []; ubrhs=[];
end 

% For fminimax and fgoalattain, an extra "slack" 
% variable (gamma) is added to create the minimax/goal attain
% objective function.  Add an extra element to lb/ub so
% that gamma is unconstrained but we can avoid out of index
% errors for lb/ub (when doing finite-differencing).
if  strcmp(caller,'fminimax') || strcmp(caller,'fgoalattain')
    lb(end+1) = -Inf;
    ub(end+1) = Inf;
end

% Update constraint matrix and right hand side vector with bound constraints.
A = [lbmatrix;ubmatrix;Ain];
B = [lbrhs;ubrhs;Bin];
if isempty(A)
    A = zeros(0,numberOfVariables); B=zeros(0,1);
end
if isempty(Aeq)
    Aeq = zeros(0,numberOfVariables); Beq=zeros(0,1);
end

% Used for semi-infinite optimization:
s = nan; POINT =[]; NEWLAMBDA =[]; LAMBDA = []; NPOINT =[]; FLAG = 2;
OLDLAMBDA = [];

x(:) = XOUT;  % Set x to have user expected size
% Compute the objective function and constraints
if isFseminf
    f = fval;
    [ncineq,nceq,NPOINT,NEWLAMBDA,OLDLAMBDA,LOLD,s] = ...
        semicon(x,LAMBDA,NEWLAMBDA,OLDLAMBDA,POINT,FLAG,s,varargin{:});
else
    f = fval;
    nceq = nceqval; ncineq = ncineqval;  % nonlinear constraints only
end
nc = [nceq; ncineq];
c = [ Aeq*XOUT-Beq; nceq; A*XOUT-B; ncineq];

% Get information on the number and type of constraints.
non_eq = length(nceq);
non_ineq = length(ncineq);
[lin_eq,Aeqcol] = size(Aeq);
[lin_ineq,Acol] = size(A);  % includes upper and lower bounds
eq = non_eq + lin_eq;
ineq = non_ineq + lin_ineq;
ncstr = ineq + eq;
% Boolean inequalitiesExist = true if and only if there exist either
% finite bounds or linear inequalities or nonlinear inequalities. 
% Used only for printing indices of active inequalities at the solution
inequalitiesExist = any(arglb) || any(argub) || size(Ain,1) > 0 || non_ineq > 0;

% Compute the initial constraint violation.
ga=[abs(c( (1:eq)' )) ; c( (eq+1:ncstr)' ) ];
if ~isempty(c)
   mg=max(ga);
else
   mg = 0;
end

if isempty(f)
    error('optim:nlconst:InvalidFUN', ...
          'FUN must return a non-empty objective function.')
end

% If the user-supplied nonlinear constraint gradients are sparse, 
% we have to make them full after each call to the user functions 
% and before passing them to qpsub---which would error otherwise.
if issparse(gncval) || issparse(gnceqval)
  nonlinConstrGradIsSparse = true;
  gncval = full(gncval); gnceqval = full(gnceqval); 
else
  nonlinConstrGradIsSparse = false;
end

% Get initial analytic gradients and check size.
if gradflag || gradconstflag
    if gradflag
        gf_user = gval;
    end
    if gradconstflag
        gnc_user = [gnceqval, gncval];   % Don't include A and Aeq yet
    else
        gnc_user = [];
    end
    if isempty(gnc_user) && isempty(nc)
        % Make gc compatible
        gnc = nc'; gnc_user = nc';
    end 
end

OLDX=XOUT;
OLDC=c; OLDNC=nc;
OLDgf=zeros(numberOfVariables,1);
gf=zeros(numberOfVariables,1);
OLDAN=zeros(ncstr,numberOfVariables);
LAMBDA=zeros(ncstr,1);
if isFseminf
   lambdaNLP = NEWLAMBDA; 
else
   lambdaNLP = zeros(ncstr,1);
end
numFunEvals=1;
numGradEvals=1;

% Display header information.
if meritFunctionType==1
    if isequal(caller,'fgoalattain')
        header = ...
          sprintf(['\n                 Attainment        Max     Line search     Directional \n',...
                     ' Iter F-count        factor    constraint   steplength      derivative   Procedure ']);
        
    else % fminimax
        header = ...
          sprintf(['\n                  Objective        Max     Line search     Directional \n',...
                     ' Iter F-count         value    constraint   steplength      derivative   Procedure ']);
    end
    formatstrFirstIter = '%5.0f  %5.0f   %12.6g  %12.6g                                            %s';
    formatstr = '%5.0f  %5.0f   %12.4g  %12.4g %12.3g    %12.3g   %s  %s';
else % fmincon or fseminf is caller
    header = ...
     sprintf(['\n                                Max     Line search  Directional  First-order \n',...
                ' Iter F-count        f(x)   constraint   steplength   derivative   optimality Procedure ']);
    formatstrFirstIter = '%5.0f  %5.0f %12.6g %12.4g                                         %s';
    formatstr = '%5.0f  %5.0f %12.6g %12.4g %12.3g %12.3g %12.3g %s  %s';
end

how = ''; 
optimError = []; % In case we have convergence in 0th iteration, this needs a value.
%---------------------------------Main Loop-----------------------------
while ~done 
   %----------------GRADIENTS----------------
   
   if constflag && ~gradconstflag || ~gradflag || DerivativeCheck
      % If there are nonlinear constraints and their gradients are not
      % supplied, or the objetive gradients are not supplied, or
      % derivative check is required, then compute finite difference
      % gradients.

      POINT = NPOINT; 
      len_nc = length(nc);
      ncstr =  lin_eq + lin_ineq + len_nc;     
      FLAG = 0; % For semi-infinite

      % Compute finite difference gradients
      %
      if DerivativeCheck || (~gradflag && ~gradconstflag) % No objective gradients,
                                                          % no constraint gradients
          [gf,gnc,NEWLAMBDA,OLDLAMBDA,s]=finitedifferences_mm(XOUT,x,funfcn,confcn,lb,ub,f,nc, ...
              [],[],DiffMinChange,DiffMaxChange,typicalx,[],'all', ...
              LAMBDA,NEWLAMBDA,OLDLAMBDA,POINT,FLAG,s, ...
              isFseminf,varargin{:});
          gnc = gnc'; % nlconst requires the transpose of the Jacobian
      elseif ~gradconstflag % No constraint gradients; objective
                            % gradients supplied
          [gf,gnc,NEWLAMBDA,OLDLAMBDA,s]=finitedifferences(XOUT,x,[],confcn,lb,ub,f,nc, ...
              [],[],DiffMinChange,DiffMaxChange,typicalx,[],'all', ...
              LAMBDA,NEWLAMBDA,OLDLAMBDA,POINT,FLAG,s, ...
              isFseminf,varargin{:});
          gnc = gnc'; % nlconst requires the transpose of the Jacobian
      elseif ~gradflag % No objective gradients, constraint gradients supplied
          gf=finitedifferences(XOUT,x,funfcn,[],lb,ub,f,[],[],[], ...
              DiffMinChange,DiffMaxChange,typicalx,[], ...
              'all',[],[],[],[],[],[],isFseminf,varargin{:});
      end

      % Gradient check
      if DerivativeCheck && (gradflag || gradconstflag) % analytic exists
                           
         if gradflag
            gfFD = gf;
            gf = gf_user;
            
            disp('Function derivative')
            if isa(funfcn{4},'inline')
               graderr(gfFD, gf, formula(funfcn{4}));
            else
               graderr(gfFD, gf, funfcn{4});
            end
         end
         
         if gradconstflag
            gncFD = gnc; 
            gnc = gnc_user;
            
            disp('Constraint derivative')
            if isa(confcn{4},'inline')
               graderr(gncFD, gnc, formula(confcn{4}));
            else
               graderr(gncFD, gnc, confcn{4});
            end
         end         
         DerivativeCheck = 0;
      elseif gradflag || gradconstflag
         if gradflag
            gf = gf_user;
         end
         if gradconstflag
            gnc = gnc_user;
         end
      end % DerivativeCheck == 1 &  (gradflag | gradconstflag)
      
      FLAG = 1; % For semi-infinite
      numFunEvals = numFunEvals + numberOfVariables;

   else % (~constflag | gradflag) & gradconstflag & no DerivativeCheck 
      gnc = gnc_user;
      gf = gf_user;
   end  
   
   % Now add in Aeq, and A
   if ~isempty(gnc)
      gc = [Aeq', gnc(:,1:non_eq), A', gnc(:,non_eq+1:non_ineq+non_eq)];
   elseif ~isempty(Aeq) || ~isempty(A)
      gc = [Aeq',A'];
   else
      gc = zeros(numberOfVariables,0);
   end
   AN=gc';
   
   % Iteration 0 is handled separately below
   if iter > 0 % All but 0th iteration ----------------------------------------
       % Compute the first order KKT conditions.
       if meritFunctionType == 1 
           % don't use this stopping test for fminimax or fgoalattain
           optimError = inf;
       else
           if isFseminf, lambdaNLP = NEWLAMBDA; end
           normgradLag = norm(gf + AN'*lambdaNLP,inf);
           normcomp = norm(lambdaNLP(eq+1:ncstr).*c(eq+1:ncstr),inf);
           if isfinite(normgradLag) && isfinite(normcomp)
               optimError = max(normgradLag, normcomp);
           else
               optimError = inf;
           end
       end
       feasError  = mg;
       optimScal = 1; feasScal = 1; 
       
       % Print iteration information starting with iteration 1
       if verbosity > 2
           if meritFunctionType == 1,
               gamma = f;
               CurrOutput = sprintf(formatstr,iter,numFunEvals,gamma,mg,...
                   steplength,gf'*SD,how,howqp); 
               disp(CurrOutput)
           else
               CurrOutput = sprintf(formatstr,iter,numFunEvals,f,mg,...
                   steplength,gf'*SD,optimError,how,howqp); 
               disp(CurrOutput)
           end
       end
       % OutputFcn and PlotFcns call
       if haveoutputfcn || haveplotfcn
           [xOutputfcn, optimValues, stop] = callOutputAndPlotFcns(outputfcn,plotfcns,caller,XOUT, ...
               xOutputfcn,'iter',iter,numFunEvals,f,mg,steplength,gf,SD,meritFunctionType, ...
               optimError,how,howqp,vararginOutputfcn{:});
           if stop  % Stop per user request.
               [x,FVAL,lambda_out,EXITFLAG,OUTPUT,GRADIENT,HESS] = ...
                   cleanUpInterrupt(xOutputfcn,optimValues,caller);
               if verbosity > 0
                   disp(OUTPUT.message)
               end
               return;
           end
       end
       
       %-------------TEST CONVERGENCE---------------
       % If NoStopIfFlatInfeas option is on, in addition to the objective looking
       % flat, also require that the iterate be feasible (among other things) to 
       % detect that no further progress can be made.
       if ~noStopIfFlatInfeas
         noFurtherProgress = ( max(abs(SD)) < 2*tolX || abs(gf'*SD) < 2*tolFun ) && ...
               (mg < tolCon || infeasIllPosedMaxSQPIter);
       else
         noFurtherProgress = ( abs(steplength)*max(abs(SD)) < 2*tolX || (abs(gf'*SD) < 2*tolFun && ...
               feasError < tolCon*feasScal) ) && ( mg < tolCon || infeasIllPosedMaxSQPIter );
       end
         
       if optimError < tolFun*optimScal && feasError < tolCon*feasScal
           outMessage = ...
             sprintf(['Optimization terminated: first-order optimality measure less\n' ...
                      ' than options.TolFun and maximum constraint violation is less\n' ...
                      ' than options.TolCon.']);
           if verbosity > 1
               disp(outMessage) 
           end
           EXITFLAG = 1;
           done = true;

           if inequalitiesExist
              % Report active inequalities
              [activeLb,activeUb,activeIneqLin,activeIneqNonlin] = ...
                  activeInequalities(c,tolCon,arglb,argub,lin_eq,non_eq,size(Ain));           

              if any(activeLb) || any(activeUb) || any(activeIneqLin) || any(activeIneqNonlin)              
                 if verbosity > 1
                    fprintf('Active inequalities (to within options.TolCon = %g):\n',tolCon)
                    disp('  lower      upper     ineqlin   ineqnonlin')
                    printColumnwise(activeLb,activeUb,activeIneqLin,activeIneqNonlin);
                 end
              else
                 if verbosity > 1
                    disp('No active inequalities.')
                 end 
              end 
           end   
       elseif noFurtherProgress
           % The algorithm can make no more progress.  If feasible, compute 
           % the new up-to-date Lagrange multipliers (with new gradients) 
           % and recompute the KKT error.  Then output appropriate termination
           % message.
           if mg < tolCon
               if meritFunctionType == 1
                   optimError = inf;
               else
                   lambdaNLP(:,1) = 0;
                   [Q,R] = qr(AN(ACTIND,:)');
                   ws = warning('off');
                   lambdaNLP(ACTIND) = -R\Q'*gf;
                   warning(ws);
                   lambdaNLP(eq+1:ncstr) = max(0,lambdaNLP(eq+1:ncstr));
                   if isFseminf, lambdaNLP = NEWLAMBDA; end
                   normgradLag = norm(gf + AN'*lambdaNLP,inf);
                   normcomp = norm(lambdaNLP(eq+1:ncstr).*c(eq+1:ncstr),inf);
                   if isfinite(normgradLag) && isfinite(normcomp)
                       optimError = max(normgradLag, normcomp);
                   else
                       optimError = inf;
                   end
               end
               optimScal = 1;
               if optimError < tolFun*optimScal
                   outMessage = ...
                     sprintf(['Optimization terminated: first-order optimality ' ...
                              'measure less than options.TolFun\n and maximum ' ...
                              'constraint violation is less than options.TolCon.']);
                   if verbosity > 1
                       disp(outMessage)
                   end
                   EXITFLAG = 1;
               elseif max(abs(SD)) < 2*tolX
                   outMessage = ...
                     sprintf(['Optimization terminated: magnitude of search direction less than 2*options.TolX\n' ...
                              ' and maximum constraint violation is less than options.TolCon.']);
                   if verbosity > 1
                       disp(outMessage)
                   end
                   EXITFLAG = 4;
               else 
                   outMessage = ...
                      sprintf(['Optimization terminated: magnitude of directional derivative in search\n' ... 
                               ' direction less than 2*options.TolFun and maximum constraint violation\n' ...
                               '  is less than options.TolCon.']);
                   if verbosity > 1 
                       disp(outMessage) 
                   end
                   EXITFLAG = 5;
               end 
               
               if inequalitiesExist
                  % Report active inequalities
                  [activeLb,activeUb,activeIneqLin,activeIneqNonlin] = ...
                      activeInequalities(c,tolCon,arglb,argub,lin_eq,non_eq,size(Ain));  

                  if any(activeLb) || any(activeUb) || any(activeIneqLin) || any(activeIneqNonlin)
                     if verbosity > 1
                        fprintf('Active inequalities (to within options.TolCon = %g):\n', tolCon)
                        disp('  lower      upper     ineqlin   ineqnonlin')
                        printColumnwise(activeLb,activeUb,activeIneqLin,activeIneqNonlin);
                     end
                  else
                     if verbosity > 1
                        disp('No active inequalities.')
                     end
                  end
               end
           else                         % if mg >= tolCon
               if max(abs(SD)) < 2*tolX
                   outMessage = ...
                      sprintf(['Optimization terminated: no feasible solution found. Magnitude of search\n', ...
                               ' direction less than 2*options.TolX but constraints are not satisfied.']);
               else
                   outMessage = sprintf(['Optimization terminated: no feasible solution found.\n' ...
                                        '  Magnitude of directional derivative in search direction\n', ...
                                        '  less than 2*options.TolFun but constraints are not satisfied.']);
               end
               if strcmp(howqp,'MaxSQPIter')
                   outMessage = sprintf(['Optimization terminated: no feasible solution found.\n' ...
                           ' During the solution to the last quadratic programming subproblem, the\n' ...
                           ' maximum number of iterations was reached. Increase options.MaxSQPIter.']);
               end 
               EXITFLAG = -2;
               if verbosity > 0
                 disp(outMessage)
               end
           end                          % of "if mg < tolCon"
           done = true;
       else % continue
           % NEED=[LAMBDA>0] | G>0
           if numFunEvals > maxFunEvals
               XOUT = MATX;
               f = OLDF;
               gf = OLDgf;
               outMessage = sprintf(['Maximum number of function evaluations exceeded;\n' ...
                                         ' increase OPTIONS.MaxFunEvals.']);
               if verbosity > 0
                   disp(outMessage)
               end
               EXITFLAG = 0;
               done = true;
           end
           if iter >= maxIter
               XOUT = MATX;
               f = OLDF;
               gf = OLDgf;
               outMessage = sprintf(['Maximum number of iterations exceeded;\n' ...
                                         ' increase OPTIONS.MaxIter.']);
               if verbosity > 0
                   disp(outMessage)
               end
               EXITFLAG = 0;
               done = true;
           end
       end 
   else % ------------------------0th Iteration----------------------------------
       if verbosity > 2
           disp(header)
           % Print 0th iteration information (some columns left blank)
           if meritFunctionType == 1,
               gamma = f;
               CurrOutput = sprintf(formatstrFirstIter,iter,numFunEvals,gamma,mg,how); 
               disp(CurrOutput)
           else
               if mg > tolCon
                   how = 'Infeasible start point';
               else
                   how = '';
               end
               CurrOutput = sprintf(formatstrFirstIter,iter,numFunEvals,f,mg,how); 
               disp(CurrOutput)
           end
       end
       
       % Initialize the output and plot functions.
       if haveoutputfcn || haveplotfcn
           [xOutputfcn, optimValues, stop] = callOutputAndPlotFcns(outputfcn,plotfcns,caller,XOUT, ...
               xOutputfcn,'init',iter,numFunEvals,f,mg,[],gf,[],meritFunctionType,[],[],[], ...
               vararginOutputfcn{:});
           if stop
               [x,FVAL,lambda_out,EXITFLAG,OUTPUT,GRADIENT,HESS] = cleanUpInterrupt(xOutputfcn,optimValues,caller);
               if verbosity > 0
                   disp(OUTPUT.message)
               end
               return;
           end
           
           % OutputFcn call for 0th iteration
           [xOutputfcn, optimValues, stop] = callOutputAndPlotFcns(outputfcn,plotfcns,caller,XOUT, ...
               xOutputfcn,'iter',iter,numFunEvals,f,mg,[],gf,[],meritFunctionType,[],how,'', ...
               vararginOutputfcn{:});
           if stop  % Stop per user request.
               [x,FVAL,lambda_out,EXITFLAG,OUTPUT,GRADIENT,HESS] = ...
                   cleanUpInterrupt(xOutputfcn,optimValues,caller);
               if verbosity > 0
                   disp(OUTPUT.message)
               end
               return;
           end
           
       end % if haveoutputfcn || haveplotfcn
   end % if iter > 0
   
   % Continue if termination criteria do not hold or it is the 0th iteration-------------------------------------------
   if ~done 
      how=''; 
      iter = iter + 1;

      %-------------SEARCH DIRECTION---------------
      % For equality constraints make gradient face in 
      % opposite direction to function gradient.
      for i=1:eq 
         schg=AN(i,:)*gf;
         if schg>0
            AN(i,:)=-AN(i,:);
            c(i)=-c(i);
         end
      end
   
      if numGradEvals>1  % Check for first call    
         if meritFunctionType~=5,   
            NEWLAMBDA=LAMBDA; 
         end
         [ma,na] = size(AN);
         GNEW=gf+AN'*NEWLAMBDA;
         GOLD=OLDgf+OLDAN'*LAMBDA;
         YL=GNEW-GOLD;
         sdiff=XOUT-OLDX;

         % Make sure Hessian is positive definite in update.
         if YL'*sdiff<steplength^2*1e-3
            while YL'*sdiff<-1e-5
               [YMAX,YIND]=min(YL.*sdiff);
               YL(YIND)=YL(YIND)/2;
               % XYZ testen, ob 
               if ~isreal(YL)
                   YL=real(YL);
               end
            end
            if YL'*sdiff < (eps*norm(HESS,'fro'));
               how=' Hessian modified twice';
               FACTOR=AN'*c - OLDAN'*OLDC;
               FACTOR=FACTOR.*(sdiff.*FACTOR>0).*(YL.*sdiff<=eps);
               WT=1e-2;
               if max(abs(FACTOR))==0; FACTOR=1e-5*sign(sdiff); end
               while YL'*sdiff < (eps*norm(HESS,'fro')) && WT < 1/eps
                  YL=YL+WT*FACTOR;
                  WT=WT*2;
               end
            else
               how=' Hessian modified';
            end
         end
         
         if haveoutputfcn
             % Use the xOutputfcn and optimValues from last call to outputfcn (do not call
             % callOutputAndPlotFcn) 
             % Call output functions via callAllOptimOutputFcns wrapper
             stop = callAllOptimOutputFcns(outputfcn,xOutputfcn,optimValues,'interrupt',vararginOutputfcn{:});
             if stop
                 [x,FVAL,lambda_out,EXITFLAG,OUTPUT,GRADIENT,HESS] = ...
                     cleanUpInterrupt(xOutputfcn,optimValues,caller);
                 if verbosity > 0
                     disp(OUTPUT.message)
                 end
                 return;
             end
         end
         
         %----------Perform BFGS Update If YL'S Is Positive---------
         if YL'*sdiff>eps
             if isinf(1/(sdiff'*HESS*sdiff)) % Fall abfangen, dass durch Null geteilt wird
                 how=' Hessian not updated';
             else % Original
                 HESS=HESS ...
                 +(YL*YL')/(YL'*sdiff)-((HESS*sdiff)*(sdiff'*HESS'))/(sdiff'*HESS*sdiff);
             end
             % BFGS Update using Cholesky factorization  of Gill, Murray and Wright.
             % In practice this was less robust than above method and slower. 
             %   R=chol(HESS); 
             %   s2=R*S; y=R'\YL; 
             %   W=eye(numberOfVariables,numberOfVariables)-(s2'*s2)\(s2*s2') + (y'*s2)\(y*y');
             %   HESS=R'*W*R;
         else
            how=' Hessian not updated';
         end
      else % First call
         OLDLAMBDA=repmat(eps+gf'*gf,ncstr,1)./(sum(AN'.*AN')'+eps);
         ACTIND = 1:eq;     
      end % if numGradEvals>1
      numGradEvals=numGradEvals+1;
   
      LOLD=LAMBDA;
      OLDAN=AN;
      OLDgf=gf;
      OLDC=c;
      OLDF=f;
      OLDX=XOUT;
      XN=zeros(numberOfVariables,1);
      if (meritFunctionType>0 && meritFunctionType<5)
         % Minimax and attgoal problems have special Hessian:
         HESS(numberOfVariables,1:numberOfVariables)=zeros(1,numberOfVariables);
         HESS(1:numberOfVariables,numberOfVariables)=zeros(numberOfVariables,1);
         HESS(numberOfVariables,numberOfVariables)=1e-8*norm(HESS,'inf');
         XN(numberOfVariables)=max(c); % Make a feasible solution for qp
      end
   
      GT =c;
   
      HESS = (HESS + HESS')*0.5;
   
      [SD,lambda,exitflagqp,outputqp,howqp,ACTIND] ...
         = qpsub_mm(HESS,gf,AN,-GT,[],[],XN,eq,-1, ...
         Nlconst,size(AN,1),numberOfVariables,OPTIONS,defaultopt,ACTIND,phaseOneTotalScaling);
    
      lambdaNLP(:,1) = 0;
      lambdaNLP(ACTIND) = lambda(ACTIND);
      lambda((1:eq)') = abs(lambda( (1:eq)' ));
      ga=[abs(c( (1:eq)' )) ; c( (eq+1:ncstr)' ) ];
      if ~isempty(c)
          mg = max(ga);
      else
          mg = 0;
      end

      if strncmp(howqp,'ok',2); 
          howqp =''; 
      end
      if ~isempty(how) && ~isempty(howqp) 
          how = [how,'; '];
      end

      LAMBDA=lambda((1:ncstr)');
      OLDLAMBDA=max([LAMBDA';0.5*(LAMBDA+OLDLAMBDA)'])' ;

      %---------------LINESEARCH--------------------
      MATX=XOUT;
      MATL = f+sum(OLDLAMBDA.*(ga>0).*ga) + 1e-30;

      infeasIllPosedMaxSQPIter = strcmp(howqp,'infeasible') || ...
          strcmp(howqp,'ill posed') || strcmp(howqp,'MaxSQPIter');
      if meritFunctionType==0 || meritFunctionType == 5
         % This merit function looks for improvement in either the constraint
         % or the objective function unless the sub-problem is infeasible in which
         % case only a reduction in the maximum constraint is tolerated.
         % This less "stringent" merit function has produced faster convergence in
         % a large number of problems.
         if mg > 0
            MATL2 = mg;
         elseif f >=0 
            MATL2 = -1/(f+1);
         else 
            MATL2 = 0;
         end
         if ~infeasIllPosedMaxSQPIter && f < 0
            MATL2 = MATL2 + f - 1;
         end
      else
         % Merit function used for MINIMAX or ATTGOAL problems.
         MATL2=mg+f;
      end
      if mg < eps && f < bestf
         bestf = f;
         bestx = XOUT;
         bestHess = HESS;
         bestgrad = gf;
         bestlambda = lambda;
         bestmg = mg;
         bestOptimError = optimError;
      end
      MERIT = MATL + 1;
      MERIT2 = MATL2 + 1; 
      steplength=2;
      while  (MERIT2 > MATL2) && (MERIT > MATL) ...
            && numFunEvals < maxFunEvals
         steplength=steplength/2;
         if steplength < 1e-4,  
            steplength = -steplength; 
         
            % Semi-infinite may have changing sampling interval
            % so avoid too stringent check for improvement
            if meritFunctionType == 5, 
               steplength = -steplength; 
               MATL2 = MATL2 + 10; 
            end
         end
         if hasBoundOnStep && (iter <= relLineSrchBndDuration)
           % Bound total displacement:
           % |steplength*SD(i)| <= relLineSrchBnd*max(|x(i)|, |typicalx(i)|)
           % for all i.
           indxViol = abs(steplength*SD) > relLineSrchBnd*max(abs(MATX),abs(typicalx));
           if any(indxViol)
             steplength = sign(steplength)*min(  min( abs(steplength), ...
                  relLineSrchBnd*max(abs(MATX(indxViol)),abs(typicalx(indxViol))) ...
                  ./abs(SD(indxViol)) )  );
           end   
         end
         
         XOUT = MATX + steplength*SD;
         x(:)=XOUT; 
      
         if isFseminf
            f = feval(funfcn{3},x,varargin{3:end});
         
            [nctmp,nceqtmp,NPOINT,NEWLAMBDA,OLDLAMBDA,LOLD,s] = ...
               semicon(x,LAMBDA,NEWLAMBDA,OLDLAMBDA,POINT,FLAG,s,varargin{:});
            nctmp = nctmp(:); nceqtmp = nceqtmp(:);
            non_ineq = length(nctmp);  % the length of nctmp can change
            ineq = non_ineq + lin_ineq;
            ncstr = ineq + eq;
            % Possibly changed constraints, even if same number,
            % so ACTIND may be invalid.
            ACTIND = 1:eq;
         else
            f = feval(funfcn{3},x,varargin{:});
            if constflag
               [nctmp,nceqtmp] = feval(confcn{3},x,varargin{:});
               nctmp = nctmp(:); nceqtmp = nceqtmp(:);
            else
               nctmp = []; nceqtmp=[];
            end
         end
         numFunEvals = numFunEvals + 1;
            
         nc = [nceqtmp(:); nctmp(:)];
         c = [Aeq*XOUT-Beq; nceqtmp(:); A*XOUT-B; nctmp(:)];  

         ga=[abs(c( (1:eq)' )) ; c( (eq+1:length(c))' )];
         if ~isempty(c)
            mg=max(ga);
         else
            mg = 0;
         end

         MERIT = f+sum(OLDLAMBDA.*(ga>0).*ga);
         if meritFunctionType == 0 || meritFunctionType == 5
            if mg > 0
               MERIT2 = mg;
            elseif f >=0 
               MERIT2 = -1/(f+1);
            else 
               MERIT2 = 0;
            end
            if ~infeasIllPosedMaxSQPIter && f < 0
               MERIT2 = MERIT2 + f - 1;
            end
         else
            MERIT2=mg+f;
         end
         if haveoutputfcn % Call output functions via callAllOptimOutputFcns wrapper
             stop = callAllOptimOutputFcns(outputfcn,xOutputfcn,optimValues,'interrupt',vararginOutputfcn{:});
             if stop
                 [x,FVAL,lambda_out,EXITFLAG,OUTPUT,GRADIENT,HESS] = ...
                     cleanUpInterrupt(xOutputfcn,optimValues,caller);
                 if verbosity > 0
                     disp(OUTPUT.message)
                 end
                 return;
             end
             
         end

                                                                                                                                                                                                                            end  % line search loop
      %------------Finished Line Search-------------
   
      if meritFunctionType~=5
         mf=abs(steplength);
         LAMBDA=mf*LAMBDA+(1-mf)*LOLD;
      end

      x(:) = XOUT;
      switch funfcn{1} % evaluate function gradients
      case 'fun'
         ;  % do nothing...will use finite difference.
      case 'fungrad'
         [f,gf_user] = feval(funfcn{3},x,varargin{:});
         gf_user = gf_user(:);
         numGradEvals=numGradEvals+1;
         numFunEvals=numFunEvals+1;
      case 'fun_then_grad'
         gf_user = feval(funfcn{4},x,varargin{:});
         gf_user = gf_user(:);
         numGradEvals=numGradEvals+1;
      otherwise
         error('optim:nlconst:UndefinedCalltypeInFMINCON', ...
               'Undefined calltype in FMINCON.');
      end
      
      % Evaluate constraint gradients
      switch confcn{1}
      case 'fun'
         gnceq=[]; gncineq=[];
      case 'fungrad'
         [nctmp,nceqtmp,gncineq,gnceq] = feval(confcn{3},x,varargin{:});
         nctmp = nctmp(:); nceqtmp = nceqtmp(:);
         numGradEvals=numGradEvals+1;
         % Objective/constraint evaluation counted above in evaluation of obj block
      case 'fun_then_grad'
         [gncineq,gnceq] = feval(confcn{4},x,varargin{:});
         numGradEvals=numGradEvals+1;
      case ''
         nctmp=[]; nceqtmp =[];
         gncineq = zeros(numberOfVariables,length(nctmp));
         gnceq = zeros(numberOfVariables,length(nceqtmp));
      otherwise
         error('optim:nlconst:UndefinedCalltypeInFMINCON', ...
               'Undefined calltype in FMINCON.');
      end
      % Make sure the Jacobian matrix is full before passing it
      % to qpsub
      if nonlinConstrGradIsSparse
        gncineq = full(gncineq); gnceq = full(gnceq);
      end      
      gnc_user = [gnceq, gncineq];
      gc = [Aeq', gnceq, A', gncineq];
   
   end % if ~done   
end % while ~done


% Update 
numConstrEvals = numGradEvals;

% Gradient is in the variable gf
GRADIENT = gf;

% If a better solution was found earlier, use it:
if f > bestf 
   XOUT = bestx;
   f = bestf;
   HESS = bestHess;
   GRADIENT = bestgrad;
   lambda = bestlambda;
   mg = bestmg;
   gf = bestgrad;
   optimError = bestOptimError;
end

FVAL = f;
x(:) = XOUT;

if haveoutputfcn || haveplotfcn
    [xOutputfcn, optimValues] = callOutputAndPlotFcns(outputfcn,plotfcns,caller,XOUT,xOutputfcn,'done', ...
        iter,numFunEvals,f,mg,steplength,gf,SD,meritFunctionType,optimError,how,howqp, ...
        vararginOutputfcn{:});
    % Do not check value of 'stop' as we are done with the optimization
    % already.
end

OUTPUT.iterations = iter;
OUTPUT.funcCount = numFunEvals;
OUTPUT.lssteplength = steplength;
OUTPUT.stepsize = abs(steplength) * norm(SD);
OUTPUT.algorithm = 'medium-scale: SQP, Quasi-Newton, line-search';
if meritFunctionType == 1
   OUTPUT.firstorderopt = [];
else   
   OUTPUT.firstorderopt = optimError;
end
OUTPUT.message = outMessage;

[lin_ineq,Acol] = size(Ain);  % excludes upper and lower

lambda_out.lower=zeros(lenlb,1);
lambda_out.upper=zeros(lenub,1);

lambda_out.eqlin = lambdaNLP(1:lin_eq);
ii = lin_eq ;
lambda_out.eqnonlin = lambdaNLP(ii+1: ii+ non_eq);
ii = ii+non_eq;
lambda_out.lower(arglb) = lambdaNLP(ii+1 :ii+nnz(arglb));
ii = ii + nnz(arglb) ;
lambda_out.upper(argub) = lambdaNLP(ii+1 :ii+nnz(argub));
ii = ii + nnz(argub);
lambda_out.ineqlin = lambdaNLP(ii+1: ii + lin_ineq);
ii = ii + lin_ineq ;
lambda_out.ineqnonlin = lambdaNLP(ii+1 : end);

% NLCONST finished
%--------------------------------------------------------------------------
function [xOutputfcn, optimValues, stop] = callOutputAndPlotFcns(outputfcn,plotfcns,caller, ...
    x,xOutputfcn,state,iter,numFunEvals,f,mg,steplength,gf,SD,meritFunctionType,optimError, ...
    how,howqp,varargin)
% CALLOUTPUTANDPLOTFCN assigns values to the struct OptimValues and then calls the
% outputfcn/plotfcns.  
%
% The input STATE can have the values 'init','iter', or 'done'. 
% We do not handle the case 'interrupt' because we do not want to update
% xOutputfcn or optimValues (since the values could be inconsistent) before calling
% the outputfcn; in that case the outputfcn is called directly rather than
% calling it inside callOutputAndPlotFcns.
%
% For the 'done' state we do not check the value of 'stop' because the
% optimization is already done.

optimValues.iteration = iter;
optimValues.funccount = numFunEvals;
optimValues.fval = f;
optimValues.constrviolation = mg;
optimValues.lssteplength = steplength;
optimValues.stepsize = abs(steplength) * norm(SD); 
if ~isempty(SD)
    optimValues.directionalderivative = gf'*SD;  
else
    optimValues.directionalderivative = [];
end
optimValues.gradient = gf;
optimValues.searchdirection = SD;
if meritFunctionType == 1
    optimValues.firstorderopt = [];
else
    optimValues.firstorderopt = optimError;
end
optimValues.procedure = [how,'  ',howqp];
% Set x to have user expected size
if strcmp(caller,'fmincon') || strcmp(caller,'fseminf')
    xOutputfcn(:) = x;
else % fgoalattain and fminimax
    xOutputfcn(:) = x(1:end-1); % remove artificial variable
end

stop = false;
% callOutputAndPlotFcn is not called with state='interrupt', that's why
% this value is missing in the switch-case below. When state='interrupt',
% the output function is called directly, not via callOutputAndPlotFcns.
if ~isempty(outputfcn)
    switch state
        case {'iter','init'}
            stop = callAllOptimOutputFcns(outputfcn,xOutputfcn,optimValues,state,varargin{:}) || stop;
        case 'done'
            callAllOptimOutputFcns(outputfcn,xOutputfcn,optimValues,state,varargin{:});
        otherwise
            error('optim:nlconst:UnknownStateInCALLOUTPUTANDPLOTFCNS', ...
                'Unknown state in CALLOUTPUTANDPLOTFCNS.')
    end
end
% Call plot functions
if ~isempty(plotfcns)
    switch state
        case {'iter','init'}
            stop = callAllOptimPlotFcns(plotfcns,xOutputfcn,optimValues,state,varargin{:}) || stop; 
        case 'done'
            callAllOptimPlotFcns(plotfcns,xOutputfcn,optimValues,state,varargin{:});
        otherwise
            error('optim:nlconst:UnknownStateInCALLOUTPUTANDPLOTFCNS', ...
                'Unknown state in CALLOUTPUTANDPLOTFCNS.')
    end
end
%--------------------------------------------------------------------------
function [x,FVAL,lambda_out,EXITFLAG,OUTPUT,GRADIENT,HESS] = cleanUpInterrupt(xOutputfcn,optimValues,caller)
% CLEANUPINTERRUPT updates or sets all the output arguments of NLCONST when the optimization 
% is interrupted.  The HESSIAN and LAMBDA are set to [] as they may be in a
% state that is inconsistent with the other values since we are
% interrupting mid-iteration.

if strcmp(caller,'fmincon') || strcmp(caller,'fseminf')
    x = xOutputfcn;
else % fgoalattain or fminimax
    % fgoalattain and fminimax expect that nlconst return
    % (a) a column vector, and (b) with additional artificial
    % scalar variable (which gets discarded on return)
    dummyVariable = 0;
    x = [xOutputfcn(:); dummyVariable];
end

FVAL = optimValues.fval;
EXITFLAG = -1; 
OUTPUT.iterations = optimValues.iteration;
OUTPUT.funcCount = optimValues.funccount;
OUTPUT.stepsize = optimValues.stepsize;
OUTPUT.lssteplength = optimValues.lssteplength;
OUTPUT.algorithm = 'medium-scale: SQP, Quasi-Newton, line-search';
OUTPUT.firstorderopt = optimValues.firstorderopt; 
OUTPUT.message = 'Optimization terminated prematurely by user.';
GRADIENT = optimValues.gradient;
HESS = []; % May be in an inconsistent state
lambda_out = []; % May be in an inconsistent state

%--------------------------------------------------------------------------
function [activeLb,activeUb,activeIneqLin,activeIneqNonlin] = ...
    activeInequalities(c,tol,arglb,argub,linEq,nonlinEq,linIneq)
% ACTIVEINEQUALITIES returns the indices of the active inequalities
% and bounds.
% INPUT:
% c                 vector of constraints and bounds (see nlconst main code)
% tol               tolerance to determine when an inequality is active
% arglb, argub      boolean vectors indicating finite bounds (see nlconst
%                   main code)
% linEq             number of linear equalities
% nonlinEq          number of nonlinear equalities
% linIneq           number of linear inequalities
%
% OUTPUT
% activeLB          indices of active lower bounds
% activeUb          indices of active upper bounds  
% activeIneqLin     indices of active linear inequalities
% activeIneqNonlin  indices of active nonlinear inequalities
%

% We check wether a constraint is active or not using '< tol'
% instead of '<= tol' to be onsistent with nlconst main code, 
% where feasibility is checked using '<'.
finiteLb = nnz(arglb); % number of finite lower bounds
finiteUb = nnz(argub); % number of finite upper bounds

indexFiniteLb = find(arglb); % indices of variables with LB
indexFiniteUb = find(argub); % indices of variables with UB

% lower bounds
i = linEq + nonlinEq; % skip equalities

% Boolean vector that indicates which among the finite
% bounds is active
activeFiniteLb = abs(c(i + 1 : i + finiteLb)) < tol;

% indices of the finite bounds that are active
activeLb = indexFiniteLb(activeFiniteLb);

% upper bounds
i = i + finiteLb;

% Boolean vector that indicates which among the finite
% bounds is active
activeFiniteUb = abs(c(i + 1 : i + finiteUb)) < tol;

% indices of the finite bounds that are active
activeUb = indexFiniteUb(activeFiniteUb);

% linear inequalities
i = i + finiteUb;
activeIneqLin = find(abs(c(i + 1 : i + linIneq)) < tol); 
% nonlinear inequalities
i = i + linIneq;
activeIneqNonlin = find(abs(c(i + 1 : end)) < tol);   

% %--------------------------------------------------------------------------
% function printColumnwise(a,b,c,d)
% % PRINTCOLUMNWISE prints vectors a, b, c, d (which
% % in general have different lengths) column-wise.
% % 
% % Example: if a = [1 2], b = [4 6 7], c = [], d = [8 11 13 15]
% % then this function will produce the output (without the headers):
% %
% % a  b  c   d
% %-------------
% % 1  4      8
% % 2  6     11
% %    7     13
% %          15
% %
% length1 = length(a); length2 = length(b);
% length3 = length(c); length4 = length(d);
% 
% for k = 1:max([length1,length2,length3,length4])
%     % fprintf stops printing numbers as soon as it encounters [].
%     % To avoid this, we convert all numbers to string
%     % (fprintf doesn't stop when it comes across the blank
%     % string ' '.)
%    if k <= length1
%       value1 = num2str(a(k));
%    else
%       value1 = ' ';
%    end
%    if k <= length2
%       value2 = num2str(b(k));
%    else
%       value2 = ' ';
%    end   
%    if k <= length3
%       value3 = num2str(c(k));
%    else
%       value3 = ' ';
%    end      
%    if k <= length4
%       value4 = num2str(d(k));
%    else
%       value4 = ' ';
%    end  
%    fprintf('%5s %10s %10s %10s\n',value1,value2,value3,value4);
% end

% %--------------------------------------------------------------------------
% function [vararginOutputfcn,xOutputfcn] = getArgsForOutputAndPlotFcns(x,caller,varargin)
% %GETARGSFOROUTPUTANDPLOTFCNS sets the appropriate varargin and x values for
% % calling the output and plot functions.
% % - x contains the current values of x
% % - caller is the caller of nlconst
% % - varargin contains the user's additional parameters. If caller
% %   is fgoalattain or fminimax, it also contains some other quantities.
% 
% % For fminimax and fgoalattain, there are 6 extra varargin elements
% % preceding the extra parameters that the user passed in. 
% % Need to pass to the output/plot functions only the user additional
% % parameters, getting rid of the extra ones.
% % For fseminf this is also true, but there are only 2 extra arguments.
% if strcmp(caller,'fmincon')
%     vararginOutputfcn = varargin;
%     xOutputfcn = x; % x original shape
% elseif strcmp(caller,'fminimax') || strcmp(caller,'fgoalattain')
%     vararginOutputfcn = varargin(7:end);
%     xOutputfcn = varargin{6}; % x original shape
% else % fseminf
%     vararginOutputfcn = varargin(3:end);
%     xOutputfcn = x; % x original shape
% end
% 
% 
% 
% 
% 
% 
function [allfcns,idandmsg] = optimfcnchk_mm(funstr,caller,lenVarIn,funValCheck, ...
    gradflag,hessflag,constrflag,Algorithm,ntheta)
%OPTIMFCNCHK Pre- and post-process function expression for FCNCHK.
%
% This is a helper function.

%   [ALLFCNS,idandmsg] = OPTIMFCNCHK(FUNSTR,CALLER,lenVarIn,GRADFLAG) takes
%   the (nonempty) function handle or expression FUNSTR from CALLER with
%   lenVarIn extra arguments, parses it according to what CALLER is, then
%   returns a string or inline object in ALLFCNS.  If an error occurs,
%   this message is put in idandmsg.
%
%   ALLFCNS is a cell array:
%    ALLFCNS{1} contains a flag
%    that says if the objective and gradients are together in one function
%    (calltype=='fungrad') or in two functions (calltype='fun_then_grad')
%    or there is no gradient (calltype=='fun'), etc.
%    ALLFCNS{2} contains the string CALLER.
%    ALLFCNS{3}  contains the objective (or constraint) function
%    ALLFCNS{4}  contains the gradient function
%    ALLFCNS{5}  contains the hessian function (not used for constraint function).
%
%    If funValCheck is 'on', then we update the funfcn's (fun/grad/hess) so
%    they are called through CHECKFUN to check for NaN's, Inf's, or complex
%    values. Add a wrapper function, CHECKFUN, to check for NaN/complex
%    values without having to change the calls that look like this:
%    f = funfcn(x,varargin{:});
%    CHECKFUN is a nested function so we can get the 'caller', 'userfcn', and
%    'ntheta' (for fseminf constraint functions) information from this function
%    and the user's function and CHECKFUN can both be called with the same
%    arguments.

%    NOTE: we assume FUNSTR is nonempty.

% Initialize
if nargin < 9
    ntheta = 0;
    if nargin < 8
        Algorithm = [];
        if nargin < 7
            constrflag = false;
            if nargin < 6
                hessflag = false;
                if nargin < 5
                    gradflag = false;
                end
            end  
        end
    end
end
if constrflag
    graderrid = 'optimlib:optimfcnchk:NoConstraintGradientFunction';
    graderrmsg = 'Constraint gradient function expected (OPTIONS.GradConstr=''on'') but not found.';
    warnid = 'optimlib:optimfcnchk:ConstraintGradientOptionOff';
    warnstr = ...
        sprintf('%s\n%s\n%s\n','Constraint gradient function provided but OPTIONS.GradConstr=''off'';', ...
        '  ignoring constraint gradient function and using finite-differencing.', ...
        '  Rerun with OPTIONS.GradConstr=''on'' to use constraint gradient function.');
else
    graderrid = 'optimlib:optimfcnchk:NoGradientFunction';
    graderrmsg = 'Gradient function expected (OPTIONS.GradObj=''on'') but not found.';
    warnid = 'optimlib:optimfcnchk:GradientOptionOff';
    warnstr = ...
        sprintf('%s\n%s\n%s\n','Gradient function provided but OPTIONS.GradObj=''off'';', ...
        '  ignoring gradient function and using finite-differencing.', ...
        '  Rerun with OPTIONS.GradObj=''on'' to use gradient function.');

end
idandmsg='';
if isequal(caller,'fseminf')
    nonlconmsg =  'SEMINFCON must be a function.';
    nonlconid = 'optimlib:optimfcnchk:SeminfconNotAFunction';
else
    nonlconmsg =  'NONLCON must be a function.';
    nonlconid = 'optimlib:optimfcnchk:NonlconNotAFunction';
end
allfcns = {};
funfcn = [];
gradfcn = [];
hessfcn = [];
if gradflag && hessflag 
    if strcmpi(caller,'fmincon') && strcmpi(Algorithm,'interior-point')
        % fmincon interior-point doesn't take Hessian as 3rd argument 
        % of objective function - it's passed as a separate function
        calltype = 'fungrad';
    else
        calltype = 'fungradhess';
    end
elseif gradflag
    calltype = 'fungrad';
else % ~gradflag & ~hessflag,   OR  ~gradflag & hessflag: this problem handled later
    calltype = 'fun';
end

if isa(funstr, 'cell') && length(funstr)==1 % {fun}
    % take the cellarray apart: we know it is nonempty
    if gradflag
        error(graderrid,graderrmsg)
    end
    [funfcn, idandmsg] = fcnchk(funstr{1},lenVarIn);
    % Insert call to nested function checkfun which calls user funfcn
    if funValCheck
        userfcn = funfcn;
        funfcn = @checkfun; %caller and userfcn are in scope in nested checkfun
    end
    if ~isempty(idandmsg)
        if constrflag % Constraint, not objective, function, so adjust error message
            error(nonlconid,nonlconmsg);
        else
            error(idandmsg);
        end
    end
elseif isa(funstr, 'cell') && length(funstr)==2 && isempty(funstr{2}) % {fun,[]}
    if gradflag
        error(graderrid,graderrmsg)
    end
    [funfcn, idandmsg] = fcnchk(funstr{1},lenVarIn);
    if funValCheck
        userfcn = funfcn;
        funfcn = @checkfun; %caller and userfcn are in scope in nested checkfun
    end
    if ~isempty(idandmsg)
        if constrflag
            error(nonlconid,nonlconmsg);
        else
            error(idandmsg);
        end
    end

elseif isa(funstr, 'cell') && length(funstr)==2 %  {fun, grad} and ~isempty(funstr{2})

    [funfcn, idandmsg] = fcnchk(funstr{1},lenVarIn);
    if funValCheck
        userfcn = funfcn;
        funfcn = @checkfun; %caller and userfcn are in scope in nested checkfun
    end

    if ~isempty(idandmsg)
        if constrflag
            error(nonlconid,nonlconmsg);
        else
            error(idandmsg);
        end
    end
    [gradfcn, idandmsg] = fcnchk(funstr{2},lenVarIn);
    if funValCheck
        userfcn = gradfcn;
        gradfcn = @checkfun; %caller and userfcn are in scope in nested checkfun
    end
    if ~isempty(idandmsg)
        if constrflag
            error(nonlconid,nonlconmsg);
        else
            error(idandmsg);
        end
    end
    calltype = 'fun_then_grad';
    if ~gradflag
        warning(warnid,warnstr);
        calltype = 'fun';
    end
elseif isa(funstr, 'cell') && length(funstr)==3 ...
        && ~isempty(funstr{1}) && isempty(funstr{2}) && isempty(funstr{3})    % {fun, [], []}
    if gradflag
        error(graderrid,graderrmsg)
    end
    if hessflag
        error('optimlib:optimfcnchk:NoHessianFunction','Hessian function expected but not found.')
    end
    [funfcn, idandmsg] = fcnchk(funstr{1},lenVarIn);
    if funValCheck
        userfcn = funfcn;
        funfcn = @checkfun; %caller and userfcn are in scope in nested checkfun
    end
    if ~isempty(idandmsg)
        if constrflag
            error(nonlconid,nonlconmsg);
        else
            error(idandmsg);
        end
    end

elseif isa(funstr, 'cell') && length(funstr)==3 ...
        && ~isempty(funstr{2}) && ~isempty(funstr{3})     % {fun, grad, hess}
    [funfcn, idandmsg] = fcnchk(funstr{1},lenVarIn);
    if funValCheck
        userfcn = funfcn;
        funfcn = @checkfun; %caller and userfcn are in scope in nested checkfun
    end

    if ~isempty(idandmsg)
        if constrflag
            error(nonlconid,nonlconmsg);
        else
            error(idandmsg);
        end
    end
    [gradfcn, idandmsg] = fcnchk(funstr{2},lenVarIn);
    if funValCheck
        userfcn = gradfcn;
        gradfcn = @checkfun; %caller and userfcn are in scope in nested checkfun
    end

    if ~isempty(idandmsg)
        if constrflag
            error(nonlconid,nonlconmsg);
        else
            error(idandmsg);
        end
    end
    [hessfcn, idandmsg] = fcnchk(funstr{3},lenVarIn);
    if funValCheck
        userfcn = hessfcn;
        hessfcn = @checkfun; %caller and userfcn are in scope in nested checkfun
    end

    if ~isempty(idandmsg)
        if constrflag
            error(nonlconid,nonlconmsg);
        else
            error(idandmsg);
        end
    end
    calltype = 'fun_then_grad_then_hess';
    if ~hessflag && ~gradflag
        hwarnstr = sprintf('%s\n%s\n%s\n','Hessian and gradient functions provided ', ...
            '  but OPTIONS.Hessian=''off'' and OPTIONS.GradObj=''off''; ignoring Hessian and gradient functions.', ...
            '  Rerun with OPTIONS.Hessian=''on'' and OPTIONS.GradObj=''on'' to use derivative functions.');
        warning('optimlib:optimfcnchk:HessianAndGradientOptionsOff',hwarnstr)
        calltype = 'fun';
    elseif hessflag && ~gradflag
        warnstr = ...
            sprintf('%s\n%s\n%s\n','Hessian and gradient functions provided ', ...
            '  but OPTIONS.GradObj=''off''; ignoring Hessian and gradient functions.', ...
            '  Rerun with OPTIONS.Hessian=''on'' and OPTIONS.GradObj=''on'' to use derivative functions.');
        warning('optimlib:optimfcnchk:GradientOptionOff',warnstr)
        calltype = 'fun';
    elseif ~hessflag && gradflag
        hwarnstr = ...
            sprintf('%s\n%s\n%s\n','Hessian function provided but OPTIONS.Hessian=''off'';', ...
            '  ignoring Hessian function,', ...
            '  Rerun with OPTIONS.Hessian=''on'' to use Hessian function.');
        warning('optimlib:optimfcnchk:HessianOptionOff',hwarnstr);
        calltype = 'fun_then_grad';
    end


elseif isa(funstr, 'cell') && length(funstr)==3 ...
        && ~isempty(funstr{2}) && isempty(funstr{3})    % {fun, grad, []}
    if hessflag
        error('optimlib:optimfcnchk:NoHessianFunction','Hessian function expected but not found.')
    end
    [funfcn, idandmsg] = fcnchk(funstr{1},lenVarIn);
    if funValCheck
        userfcn = funfcn;
        funfcn = @checkfun; %caller and userfcn are in scope in nested checkfun
    end
    if ~isempty(idandmsg)
        if constrflag
            error(nonlconid,nonlconmsg);
        else
            error(idandmsg);
        end
    end
    [gradfcn, idandmsg] = fcnchk(funstr{2},lenVarIn);
    if funValCheck
        userfcn = gradfcn;
        gradfcn = @checkfun; %caller and userfcn are in scope in nested checkfun
    end
    if ~isempty(idandmsg)
        if constrflag
            error(nonlconid,nonlconmsg);
        else
            error(idandmsg);
        end
    end
    calltype = 'fun_then_grad';
    if ~gradflag
        warning(warnid,warnstr);
        calltype = 'fun';
    end


elseif isa(funstr, 'cell') && length(funstr)==3 ...
        && isempty(funstr{2}) && ~isempty(funstr{3})     % {fun, [], hess}
    error('optimlib:optimfcnchk:NoGradientWithHessian','Hessian function given without gradient function.')

elseif ~isa(funstr, 'cell')  %Not a cell; is a string expression, function name string or inline object
    [funfcn, idandmsg] = fcnchk(funstr,lenVarIn);
    if funValCheck
        userfcn = funfcn;
        funfcn = @checkfun; %caller and userfcn are in scope in nested checkfun
    end

    if ~isempty(idandmsg)
        if constrflag
            error(nonlconid,nonlconmsg);
        else
            error(idandmsg);
        end
    end
    if gradflag % gradient and function in one function/M-file
        gradfcn = funfcn; % Do this so graderr will print the correct name
    end
    if hessflag && ~gradflag
        hwarnstr = ...
            sprintf('%s\n%s\n%s\n','OPTIONS.Hessian=''on''', ...
            '  but OPTIONS.GradObj=''off''; ignoring Hessian and gradient functions.', ...
            '  Rerun with OPTIONS.Hessian=''on'' and OPTIONS.GradObj=''on'' to use derivative functions.');
        warning('optimlib:optimfcnchk:GradientOptionOff',hwarnstr)
    end

else
    errmsg = sprintf('%s\n%s', ...
        'FUN must be a function or an inline object;', ...
        ' or, FUN may be a cell array that contains these type of objects.');
    error('optimlib:optimfcnchk:MustBeAFunction',errmsg)
end

allfcns{1} = calltype;
allfcns{2} = caller;
allfcns{3} = funfcn;
allfcns{4} = gradfcn;
allfcns{5} = hessfcn;

    %------------------------------------------------------------

    function [varargout] = checkfun(x,varargin)
    % CHECKFUN checks for complex, Inf, or NaN results from userfcn.
    % Inputs CALLER, USERFCN, and NTHETA come from the scope of OPTIMFCNCHK.
    % We do not make assumptions about f, g, or H. For generality, assume
    % they can all be matrices.
   
        if nargout == 1
            f = userfcn(x,varargin{:});
            if any(any(isnan(f)))
                error('optimlib:optimfcnchk:checkfun:NaNFval', ...
                    'User function ''%s'' returned NaN when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            elseif ~isreal(f)
                error('optimlib:optimfcnchk:checkfun:ComplexFval', ...
                    'User function ''%s'' returned a complex value when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            elseif any(any(isinf(f)))
                error('optimlib:optimfcnchk:checkfun:InfFval', ...
                    'User function ''%s'' returned Inf or -Inf when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            else
                varargout{1} = f;
            end

        elseif nargout == 2 % Two output could be f,g (from objective fcn) or c,ceq (from NONLCON)
            [f,g] = userfcn(x,varargin{:});
            if any(any(isnan(f))) || any(any(isnan(g)))
                error('optimlib:optimfcnchk:checkfun:NaNFval', ...
                    'User function ''%s'' returned NaN when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            elseif ~isreal(f) || ~isreal(g)
                error('optimlib:optimfcnchk:checkfun:ComplexFval', ...
                    'User function ''%s'' returned a complex value when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            elseif any(any(isinf(f))) || any(any(isinf(g)))
                error('optimlib:optimfcnchk:checkfun:InfFval', ...
                    'User function ''%s'' returned Inf or -Inf when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            else
                varargout{1} = f;
                varargout{2} = g;
            end

        elseif nargout == 3 % This case only happens for objective functions
            [f,g,H] = userfcn(x,varargin{:});
            if any(any(isnan(f))) || any(any(isnan(g))) || any(any(isnan(H)))
                error('optimlib:optimfcnchk:checkfun:NaNFval', ...
                    'User function ''%s'' returned NaN when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            elseif ~isreal(f) || ~isreal(g) || ~isreal(H)
                error('optimlib:optimfcnchk:checkfun:ComplexFval', ...
                    'User function ''%s'' returned a complex value when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            elseif any(any(isinf(f))) || any(any(isinf(g))) || any(any(isinf(H)))
                error('optimlib:optimfcnchk:checkfun:InfFval', ...
                    'User function ''%s'' returned Inf or -Inf when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            else
                varargout{1} = f;
                varargout{2} = g;
                varargout{3} = H;
            end
        elseif nargout == 4 & ~isequal(caller,'fseminf')
            % In this case we are calling NONLCON, e.g. for FMINCON, and
            % the outputs are [c,ceq,gc,gceq]
            [c,ceq,gc,gceq] = userfcn(x,varargin{:}); 
            if any(any(isnan(c))) || any(any(isnan(ceq))) || any(any(isnan(gc))) || any(any(isnan(gceq)))
                error('optimlib:optimfcnchk:checkfun:NaNFval', ...
                    'User function ''%s'' returned NaN when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            elseif ~isreal(c) || ~isreal(ceq) || ~isreal(gc) || ~isreal(gceq)
                error('optimlib:optimfcnchk:checkfun:ComplexFval', ...
                    'User function ''%s'' returned a complex value when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            elseif any(any(isinf(c))) || any(any(isinf(ceq))) || any(any(isinf(gc))) || any(any(isinf(gceq))) 
                error('optimlib:optimfcnchk:checkfun:InfFval', ...
                    'User function ''%s'' returned Inf or -Inf when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            else
                varargout{1} = c;
                varargout{2} = ceq;
                varargout{3} = gc;
                varargout{4} = gceq;
            end
        else % fseminf constraints have a variable number of outputs, but at 
             % least 4: see semicon.m
            % Also, don't check 's' for NaN as NaN is a valid value
            T = cell(1,ntheta);
            [c,ceq,T{:},s] = userfcn(x,varargin{:});
            nanfound = any(any(isnan(c))) || any(any(isnan(ceq)));
            complexfound = ~isreal(c) || ~isreal(ceq) || ~isreal(s);
            inffound = any(any(isinf(c))) || any(any(isinf(ceq))) || any(any(isinf(s)));
            for ii=1:length(T) % Elements of T are matrices
                if nanfound || complexfound || inffound
                    break
                end
                nanfound = any(any(isnan(T{ii})));
                complexfound = ~isreal(T{ii});
                inffound = any(any(isinf(T{ii})));
            end
            if nanfound
                error('optimlib:optimfcnchk:checkfun:NaNFval', ...
                    'User function ''%s'' returned NaN when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            elseif complexfound
                error('optimlib:optimfcnchk:checkfun:ComplexFval', ...
                    'User function ''%s'' returned a complex value when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            elseif inffound
                error('optimlib:optimfcnchk:checkfun:InfFval', ...
                    'User function ''%s'' returned Inf or -Inf when evaluated;\n %s cannot continue.', ...
                    functiontostring(userfcn),upper(caller));
            else
                varargout{1} = c;
                varargout{2} = ceq;
                varargout(3:ntheta+2) = T;
                varargout{ntheta+3} = s;
            end
        end

   % end %checkfun
    %----------------------------------------------------------
%end % optimfcnchk
% QNWLOGN Computes Gauss-Hermite nodes and weights multivariate lognormal distribution
% USAGE
%   [x,w] = qnwlogn(n,mu,var);
% INPUTS
%   n   : 1 by d vector of number of nodes for each variable
%   mu  : 1 by d mean vector
%   var : d by d positive definite covariance matrix
% OUTPUTS
%   x   : prod(n) by d matrix of evaluation nodes
%   w   : prod(n) by 1 vector of probabilities
% 
% To compute expectation of f(x), where log(x) is N(mu,var), write a
% function f that returns m-vector of values when passed an m by d
% matrix, and write [x,w]=gqnlogn(n,mu,var); Ef=w'*f(x);
%
% USES: qnwnorm

% Copyright (c) 1997-2000, Paul L. Fackler & Mario J. Miranda
% paul_fackler@ncsu.edu, miranda.4@osu.edu

function [x,w] = qnwlogn(n,mu,var)

d = length(n);
if nargin<3, var=eye(d); end
if nargin<2, mu=zeros(1,d); end
[x,w] = qnwnorm(n,mu,var);
x = exp(x);
% QNWNORM Computes nodes and weights for multivariate normal distribution
% USAGE
%   [x,w] = qnwnorm(n,mu,var);
% INPUTS
%   n   : 1 by d vector of number of nodes for each variable
%   mu  : 1 by d mean vector
%   var : d by d positive definite covariance matrix
% OUTPUTS
%   x   : prod(n) by d matrix of evaluation nodes
%   w   : prod(n) by 1 vector of probabilities
% 
% To compute expectation of f(x), where x is N(mu,var), write a
% function f that returns m-vector of values when passed an m by d
% matrix, and write [x,w]=qnwnorm(n,mu,var); E[f]=w'*f(x);
%
% USES: ckron, gridmake

% Copyright (c) 1997-2000, Paul L. Fackler & Mario J. Miranda
% paul_fackler@ncsu.edu, miranda.4@osu.edu

function [x,w] = qnwnorm(n,mu,var)

d = length(n);
if nargin<3, var=eye(d); end
if nargin<2, mu=zeros(1,d); end
if size(mu,1)>1, mu=mu'; end

x = cell(1,d);
w = cell(1,d);
for i=1:d
   [x{i},w{i}] = qnwnorm1(n(i));
end
w = ckron(w(d:-1:1));
x = gridmake(x);
x = x*chol(var)+mu(ones(prod(n),1),:);

return


% QNWNORM1 Computes nodes and weights for the univariate standard normal distribution
% USAGE
%    [x,w] = qnwnorm1(n);
% INPUTS
%   n   : number of nodes
% OUTPUTS
%   x   : n by 1 vector of evaluation nodes
%   w   : n by 1 vector of probabilities
 
% Based on an algorithm in W.H. Press, S.A. Teukolsky, W.T. Vetterling
% and B.P. Flannery, "Numerical Recipes in FORTRAN", 2nd ed.  Cambridge
% University Press, 1992.

function [x,w] = qnwnorm1(n);

maxit = 100;
pim4 = 1/pi.^0.25;
m = fix((n+1)./2);
x = zeros(n,1);
w = zeros(n,1);
for i=1:m
   % Reasonable starting values 
   if i==1;        z = sqrt(2*n+1)-1.85575*((2*n+1).^(-1/6));
      elseif i==2; z = z-1.14*(n.^0.426)./z;
      elseif i==3; z = 1.86*z+0.86*x(1);
      elseif i==4; z = 1.91*z+0.91*x(2);
      else;        z = 2*z+x(i-2);
   end;
   % root finding iterations 
   its=0;
   while its<maxit;
      its = its+1;
      p1 = pim4;
      p2 = 0;
      for j=1:n
         p3 = p2;
         p2 = p1;
         p1 = z.*sqrt(2/j).*p2-sqrt((j-1)/j).*p3;
      end;
      pp = sqrt(2*n).*p2;
      z1 = z;
      z  = z1-p1./pp;
      if abs(z-z1)<1e-14; break; end;
   end;
   if its>=maxit
      error('failure to converge in qnwnorm1')
   end
   x(n+1-i) = z;
   x(i) = -z;
   w(i) = 2./(pp.*pp);
   w(n+1-i) = w(i);
end;
w = w./sqrt(pi);
x = x*sqrt(2);
function [X,lambda,exitflag,output,how,ACTIND,msg] = ...
    qpsub_mm(H,f,A,B,lb,ub,X,neqcstr,verbosity,caller,ncstr, ...
    numberOfVariables,options,defaultopt,ACTIND,phaseOneTotalScaling)
%QPSUB solves quadratic programming problems. 
%
%   X = QPSUB(H,f,A,b) solves the quadratic programming problem:
%
%            min 0.5*x'Hx + f'x   subject to:  Ax <= b 
%             x    
%


% Define constant strings
NewtonStep = 'Newton';
NegCurv = 'negative curvature chol';   
ZeroStep = 'zero step';
SteepDescent = 'steepest descent';
Conls = 'lsqlin';
Lp = 'linprog';
Qp = 'quadprog';
Qpsub = 'qpsub';
Nlconst = 'nlconst';
how = 'ok'; 

exitflag = 1;
output = [];
msg = []; % initialize to ensure appending is successful
iterations = 0;
if nargin < 16
  phaseOneTotalScaling = false;
  if nargin < 15
    ACTIND = [];  
    if nargin < 13
        options = []; 
    end
  end
end

lb=lb(:); ub = ub(:);

if isempty(verbosity), verbosity = 1; end
if isempty(neqcstr), neqcstr = 0; end

LLS = 0;
if strcmp(caller, Conls)
    LLS = 1;
    [rowH,colH]=size(H);
    numberOfVariables = colH;
end
if strcmp(caller, Qpsub)
    normalize = -1;
else
    normalize = 1;
end

simplex_iter = 0;
if  norm(H,'inf')==0 || isempty(H), is_qp=0; else, is_qp=1; end

if LLS==1
    is_qp=0;
end

normf = 1;
if normalize > 0
    % Check for lp
    if ~is_qp && ~LLS
        normf = norm(f);
        if normf > 0
            f = f./normf;
        end
    end
end

% Handle bounds as linear constraints
arglb = ~eq(lb,-inf);
lenlb=length(lb); % maybe less than numberOfVariables due to old code
if nnz(arglb) > 0     
    lbmatrix = -eye(lenlb,numberOfVariables);
    A=[A; lbmatrix(arglb,1:numberOfVariables)]; % select non-Inf bounds
    B=[B;-lb(arglb)];
end

argub = ~eq(ub,inf);
lenub=length(ub);
if nnz(argub) > 0
    ubmatrix = eye(lenub,numberOfVariables);
    A=[A; ubmatrix(argub,1:numberOfVariables)];
    B=[B; ub(argub)];
end 

% Bounds are treated as constraints: Reset ncstr accordingly
ncstr=ncstr + nnz(arglb) + nnz(argub);

% Figure out max iteration count
% For linprog/quadprog/lsqlin/qpsub problems, use 'MaxIter' for this.
% For nlconst (fmincon, etc) problems, use 'MaxSQPIter' for this.
if isequal(caller,Nlconst)
  maxiter = optimget(options,'MaxSQPIter',defaultopt,'fast'); 
  if ischar(maxiter)
    if isequal(lower(maxiter),'10*max(numberofvariables,numberofinequalities+numberofbounds)')
      maxiter = 10*max(numberOfVariables,ncstr-neqcstr);
    else
      error('optim:qpsub:InvalidMaxSQPIter', ...
            'Option ''MaxSQPIter'' must be an integer value if not the default.')
    end
  end
elseif isequal(caller,Lp)
  maxiter = optimget(options,'MaxIter',defaultopt,'fast');
  if ischar(maxiter)
    if isequal(lower(maxiter),'10*max(numberofvariables,numberofinequalities+numberofbounds)')
      maxiter = 10*max(numberOfVariables,ncstr-neqcstr);
    else
      error('optim:qpsub:InvalidMaxIter', ...
            'Option ''MaxIter'' must be an integer value if not the default.')
    end
  end
elseif isequal(caller,Qpsub)
  % Feasible point finding phase for qpsub 
  maxiter = 10*max(numberOfVariables,ncstr-neqcstr); 
else
  maxiter = optimget(options,'MaxIter',defaultopt,'fast');
end

% Used for determining threshold for whether a direction will violate
% a constraint.
normA = ones(ncstr,1);
if normalize > 0 
    for i=1:ncstr
        n = norm(A(i,:));
        if (n ~= 0)
            A(i,:) = A(i,:)/n;
            B(i) = B(i)/n;
            normA(i,1) = n;
        end
    end
else 
    normA = ones(ncstr,1);
end
errnorm = 0.01*sqrt(eps); 

tolDep = 100*numberOfVariables*eps;      
lambda = zeros(ncstr,1);
eqix = 1:neqcstr;

% Modifications for warm-start.
% Do some error checking on the incoming working set indices.
ACTCNT = length(ACTIND);
if isempty(ACTIND)
    ACTIND = eqix;
elseif neqcstr > 0
    i = max(find(ACTIND<=neqcstr));
    if isempty(i) || i > neqcstr % safeguard which should not occur
        ACTIND = eqix;
    elseif i < neqcstr
        % A redundant equality constraint was removed on the last
        % SQP iteration.  We will go ahead and reinsert it here.
        numremoved = neqcstr - i;
        ACTIND(neqcstr+1:ACTCNT+numremoved) = ACTIND(i+1:ACTCNT);
        ACTIND(1:neqcstr) = eqix;
    end
end
aix = zeros(ncstr,1);
aix(ACTIND) = 1;
ACTCNT = length(ACTIND);
ACTSET = A(ACTIND,:);

% Check that the constraints in the initial working set are
% not dependent and find an initial point which satisfies the
% initial working set.
indepInd = 1:ncstr;
remove = [];
if ACTCNT > 0 && normalize ~= -1
    % call constraint solver
    [Q,R,A,B,X,Z,how,ACTSET,ACTIND,ACTCNT,aix,eqix,neqcstr,ncstr, ...
            remove,exitflag,msg]= ...
        eqnsolv(A,B,eqix,neqcstr,ncstr,numberOfVariables,LLS,H,X,f, ...
        normf,normA,verbosity,aix,ACTSET,ACTIND,ACTCNT,how,exitflag); 
    
    if ~isempty(remove)
        indepInd(remove)=[];
        normA = normA(indepInd);
    end
    
    if strcmp(how,'infeasible')
        % Equalities are inconsistent, so X and lambda have no valid values
        % Return original X and zeros for lambda.
        ACTIND = indepInd(ACTIND);
        output.iterations = iterations;
        exitflag = -2;
        return
    end
    
    err = 0;
    if neqcstr >= numberOfVariables
        err = max(abs(A(eqix,:)*X-B(eqix)));
        if (err > 1e-8)  % Equalities not met
            how='infeasible';
            exitflag = -2;
            msg = sprintf(['Exiting: the equality constraints are overly stringent;\n' ...
                                  ' there is no feasible solution.']);
            if verbosity > 0 
                disp(msg)
            end
            % Equalities are inconsistent, X and lambda have no valid values
            % Return original X and zeros for lambda.
            ACTIND = indepInd(ACTIND);
            output.iterations = iterations;
            return
        else % Check inequalities
            if (max(A*X-B) > 1e-8)
                how = 'infeasible';
                exitflag = -2;
                msg = sprintf(['Exiting: the constraints or bounds are overly stringent;\n' ...
                                      ' there is no feasible solution. Equality constraints have been met.']);
                if verbosity > 0
                    disp(msg)
                end
            end
        end
        % Disable the warnings about conditioning for singular and
        % nearly singular matrices
        warningstate1 = warning('off', 'MATLAB:nearlySingularMatrix');
        warningstate2 = warning('off', 'MATLAB:singularMatrix');
        if is_qp
            actlambda = -R\(Q'*(H*X+f));
        elseif LLS
            actlambda = -R\(Q'*(H'*(H*X-f)));
        else
            actlambda = -R\(Q'*f);
        end
        % Restore the warning states to their original settings
        warning(warningstate1)
        warning(warningstate2)
        lambda(indepInd(ACTIND)) = normf * (actlambda ./normA(ACTIND));
        ACTIND = indepInd(ACTIND);
        output.iterations = iterations;
        return
    end
    
    % Check whether in Phase 1 of feasibility point finding. 
    if (verbosity == -2)
        cstr = A*X-B; 
        mc=max(cstr(neqcstr+1:ncstr));
        if (mc > 0)
            X(numberOfVariables) = mc + 1;
        end
    end
else 
    if ACTCNT == 0 % initial working set is empty 
        Q = eye(numberOfVariables,numberOfVariables);
        R = [];
        Z = 1;
    else           % in Phase I and working set not empty
        [Q,R] = qr(ACTSET');
        Z = Q(:,ACTCNT+1:numberOfVariables);
    end   
end

% Find Initial Feasible Solution 
cstr = A*X-B;
if ncstr > neqcstr
    mc = max(cstr(neqcstr+1:ncstr));
else
    mc = 0;
end
if mc > eps
    quiet = -2;
    optionsPhase1 = []; % Use default options in phase 1
    ACTIND2 = 1:neqcstr;
    if ~phaseOneTotalScaling 
      A2=[[A;zeros(1,numberOfVariables)],[zeros(neqcstr,1);-ones(ncstr+1-neqcstr,1)]];
    else
      % Scale the slack variable as well
      A2 = [[A [zeros(neqcstr,1);-ones(ncstr-neqcstr,1)]./normA]; ...
            [zeros(1,numberOfVariables) -1]];
    end
    [XS,lambdaS,exitflagS,outputS,howS,ACTIND2] = ...
        qpsub_mm([],[zeros(numberOfVariables,1);1],A2,[B;1e-5], ...
        [],[],[X;mc+1],neqcstr,quiet,Qpsub,size(A2,1),numberOfVariables+1, ...
        optionsPhase1,defaultopt,ACTIND2);
    slack = XS(numberOfVariables+1);
    X=XS(1:numberOfVariables);
    cstr=A*X-B;
    if slack > eps 
        if slack > 1e-8 
            how='infeasible';
            exitflag = -2;
            msg = sprintf(['Exiting: the constraints are overly stringent;\n' ...
                                  ' no feasible starting point found.']);
            if verbosity > 0
                disp(msg)
            end
        else
            how = 'overly constrained';
            exitflag = -2;
            msg = sprintf(['Exiting: the constraints are overly stringent;\n' ...
                                  ' initial feasible point found violates constraints\n' ...
                                  ' by more than eps.']);
            if verbosity > 0
                disp(msg)
            end
        end
        lambda(indepInd) = normf * (lambdaS((1:ncstr)')./normA);
        ACTIND = 1:neqcstr;
        ACTIND = indepInd(ACTIND);
        output.iterations = iterations;
        return
    else
        % Initialize active set info based on solution of Phase I.
        %      ACTIND = ACTIND2(find(ACTIND2<=ncstr));
        ACTIND = 1:neqcstr;
        ACTSET = A(ACTIND,:);
        ACTCNT = length(ACTIND);
        aix = zeros(ncstr,1);
        aix(ACTIND) = 1;
        if ACTCNT == 0
            Q = zeros(numberOfVariables,numberOfVariables);
            R = [];
            Z = 1;
        else
            [Q,R] = qr(ACTSET');
            Z = Q(:,ACTCNT+1:numberOfVariables);
        end
    end
end

if ACTCNT >= numberOfVariables - 1  
    simplex_iter = 1; 
end
[m,n]=size(ACTSET);

% Disable the warnings about conditioning for singular and
% nearly singular matrices
warningstate1 = warning('off', 'MATLAB:nearlySingularMatrix');
warningstate2 = warning('off', 'MATLAB:singularMatrix');

if (is_qp)
    gf=H*X+f;
    %  SD=-Z*((Z'*H*Z)\(Z'*gf));
    [SD, dirType] = compdir_mm(Z,H,gf,numberOfVariables,f);

    % Check for -ve definite problems:
    %  if SD'*gf>0, is_qp = 0; SD=-SD; end
elseif (LLS)
    HXf=H*X-f;
    gf=H'*(HXf);
    HZ= H*Z;
    [mm,nn]=size(HZ);
    if mm >= nn
        %   SD =-Z*((HZ'*HZ)\(Z'*gf));
        [QHZ, RHZ] =  qr(HZ,0);
        Pd = QHZ'*HXf;
        % Now need to check which is dependent
        if min(size(RHZ))==1 % Make sure RHZ isn't a vector
            depInd = find( abs(RHZ(1,1)) < tolDep);
        else
            depInd = find( abs(diag(RHZ)) < tolDep );
        end  
    end
    if mm >= nn && isempty(depInd) % Newton step
        SD = - Z*(RHZ(1:nn, 1:nn) \ Pd(1:nn,:));
        dirType = NewtonStep;
    else % steepest descent direction
        SD = -Z*(Z'*gf);
        dirType = SteepDescent;
    end
else % lp
    gf = f;
    SD=-Z*Z'*gf;
    dirType = SteepDescent; 
    if norm(SD) < 1e-10 && neqcstr
        % This happens when equality constraint is perpendicular
        % to objective function f.x.
        actlambda = -R\(Q'*(gf));
        lambda(indepInd(ACTIND)) = normf * (actlambda ./ normA(ACTIND));
        ACTIND = indepInd(ACTIND);
        output.iterations = iterations;
        % Restore the warning states to their original settings
        warning(warningstate1)
        warning(warningstate2)
        return;
    end
end
% Restore the warning states to their original settings
warning(warningstate1)
warning(warningstate2)

oldind = 0; 

% The maximum number of iterations for a simplex type method is when ncstr >=n:
% maxiters = prod(1:ncstr)/(prod(1:numberOfVariables)*prod(1:max(1,ncstr-numberOfVariables)));

%--------------Main Routine-------------------

while iterations < maxiter
    iterations = iterations + 1;
    if isinf(verbosity)
      curr_out = sprintf('Iter: %5.0f, Active: %5.0f, step: %s, proc: %s',iterations,ACTCNT,dirType,how);
        disp(curr_out); 
    end
    
    % Find distance we can move in search direction SD before a 
    % constraint is violated.
    % Gradient with respect to search direction.
    GSD=A*SD;
    
    % Note: we consider only constraints whose gradients are greater
    % than some threshold. If we considered all gradients greater than 
    % zero then it might be possible to add a constraint which would lead to
    % a singular (rank deficient) working set. The gradient (GSD) of such
    % a constraint in the direction of search would be very close to zero.
    indf = find((GSD > errnorm * norm(SD))  &  ~aix);
    
    if isempty(indf) % No constraints to hit
        STEPMIN=1e16;
        dist=[]; ind2=[]; ind=[];
    else % Find distance to the nearest constraint
        dist = abs(cstr(indf)./GSD(indf));
        [STEPMIN,ind2] =  min(dist);
        ind2 = find(dist == STEPMIN);
        % Bland's rule for anti-cycling: if there is more than one 
        % blocking constraint then add the one with the smallest index.
        ind=indf(min(ind2));
        % Non-cycling rule:
        % ind = indf(ind2(1));
    end
    
    %----------------Update X---------------------
    
    % Assume we do not delete a constraint
    delete_constr = 0;   
    
    if ~isempty(indf) && isfinite(STEPMIN) % Hit a constraint
        if strcmp(dirType, NewtonStep)
            % Newton step and hit a constraint: LLS or is_qp
            if STEPMIN > 1  % Overstepped minimum; reset STEPMIN
                STEPMIN = 1;
                delete_constr = 1;
            end
            X = X+STEPMIN*SD;
        else
            % Not a Newton step and hit a constraint: is_qp or LLS or maybe lp
            X = X+STEPMIN*SD;  
        end              
    else %  isempty(indf) | ~isfinite(STEPMIN)
        % did not hit a constraint
        if strcmp(dirType, NewtonStep)
            % Newton step and no constraint hit: LLS or maybe is_qp
            STEPMIN = 1;   % Exact distance to the solution. Now delete constr.
            X = X + SD;
            delete_constr = 1;
        else % Not a Newton step: is_qp or lp or LLS
            
            if (~is_qp && ~LLS) || strcmp(dirType, NegCurv) % LP or neg def (implies is_qp)
                % neg def -- unbounded
                if norm(SD) > errnorm
                    if normalize < 0
                        STEPMIN=abs((X(numberOfVariables)+1e-5)/(SD(numberOfVariables)+eps));
                    else 
                        STEPMIN = 1e16;
                    end
                    X=X+STEPMIN*SD;
                    how='unbounded'; 
                    exitflag = -3;
                    msg = sprintf(['Exiting: the solution is unbounded and at infinity;\n' ...
                                          ' the constraints are not restrictive enough.']);
                    if verbosity > 0
                      disp(msg)
                    end
                else % norm(SD) <= errnorm
                    how = 'ill posed';
                    exitflag = -7;
                    msg = ...
                      sprintf(['Exiting: the search direction is close to zero; the problem\n' ...
                               ' is ill-posed. The gradient of the objective function may be\n' ...
                               ' zero or the problem may be badly conditioned.']);
                      if verbosity > 0
                        disp(msg)
                      end
                end
                ACTIND = indepInd(ACTIND);
                output.iterations = iterations;
                return
            else % singular: solve compatible system for a solution: is_qp or LLS
                if is_qp
                    projH = Z'*H*Z; 
                    Zgf = Z'*gf;
                    projSD = pinv(projH)*(-Zgf);
                else % LLS
                    projH = HZ'*HZ; 
                    Zgf = Z'*gf;
                    projSD = pinv(projH)*(-Zgf);
                end
                
                % Check if compatible
                if norm(projH*projSD+Zgf) > 10*eps*(norm(projH) + norm(Zgf))
                    % system is incompatible --> it's a "chute": use SD from compdir
                    % unbounded in SD direction
                    if norm(SD) > errnorm
                        if normalize < 0
                            STEPMIN=abs((X(numberOfVariables)+1e-5)/(SD(numberOfVariables)+eps));
                        else 
                            STEPMIN = 1e16;
                        end
                        X=X+STEPMIN*SD;
                        how='unbounded'; 
                        exitflag = -3;
                        msg = sprintf(['Exiting: the solution is unbounded and at infinity;\n' ...
                                          ' the constraints are not restrictive enough.']);
                        if verbosity > 0
                          disp(msg)
                        end
                    else % norm(SD) <= errnorm
                        how = 'ill posed';
                        exitflag = -7;
                        msg = ...
                        sprintf(['Exiting: the search direction is close to zero; the problem\n' ...
                                 ' is ill-posed. The gradient of the objective function may be\n' ...
                                 ' zero or the problem may be badly conditioned.']);
                        if verbosity > 0
                          disp(msg)
                        end                        
                    end
                    
                    ACTIND = indepInd(ACTIND);
                    output.iterations = iterations;
                    return
                else % Convex -- move to the minimum (compatible system)
                    SD = Z*projSD;
                    if gf'*SD > 0
                        SD = -SD;
                    end
                    dirType = 'singular';
                    % First check if constraint is violated.
                    GSD=A*SD;
                    indf = find((GSD > errnorm * norm(SD))  &  ~aix);
                    if isempty(indf) % No constraints to hit
                        STEPMIN=1;
                        delete_constr = 1;
                        dist=[]; ind2=[]; ind=[];
                    else % Find distance to the nearest constraint
                        dist = abs(cstr(indf)./GSD(indf));
                        [STEPMIN,ind2] =  min(dist);
                        ind2 = find(dist == STEPMIN);
                        % Bland's rule for anti-cycling: if there is more than one 
                        % blocking constraint then add the one with the smallest index.
                        ind=indf(min(ind2));
                    end
                    if STEPMIN > 1  % Overstepped minimum; reset STEPMIN
                        STEPMIN = 1;
                        delete_constr = 1;
                    end
                    X = X + STEPMIN*SD; 
                end
            end % if ~is_qp | smallRealEig < -eps
        end % if strcmp(dirType, NewtonStep)
    end % if ~isempty(indf)& isfinite(STEPMIN) % Hit a constraint
    
    % Calculate gradient w.r.t objective at this point
    if is_qp
        gf=H*X+f;
    elseif LLS % LLS
        gf=H'*(H*X-f);
        % else gf=f still true.
    end
    
    %----Check if reached minimum in current subspace-----
    
    if delete_constr
        % Note: only reach here if a minimum in the current subspace found
        %       LP's do not enter here.
        if ACTCNT>0
            % Disable the warnings about conditioning for singular and
            % nearly singular matrices
            warningstate1 = warning('off', 'MATLAB:nearlySingularMatrix');
            warningstate2 = warning('off', 'MATLAB:singularMatrix');
            if is_qp
                rlambda = -R\(Q'*gf);
            elseif LLS
                rlambda = -R\(Q'*gf);
                % else: lp does not reach this point
            end
            actlambda = rlambda;
            actlambda(eqix) = abs(rlambda(eqix));
            indlam = find(actlambda < 0);
            if (~length(indlam)) 
                lambda(indepInd(ACTIND)) = normf * (rlambda./normA(ACTIND));
                ACTIND = indepInd(ACTIND);
                output.iterations = iterations;
                % Restore the warning states to their original settings
                warning(warningstate1)
                warning(warningstate2)
                return
            end
            % Remove constraint
            lind = find(ACTIND == min(ACTIND(indlam)));
            lind = lind(1);
            ACTSET(lind,:) = [];
            aix(ACTIND(lind)) = 0;
            [Q,R]=qrdelete(Q,R,lind);
            ACTIND(lind) = [];
            ACTCNT = length(ACTIND);
            simplex_iter = 0;
            ind = 0;
            % Restore the warning states to their original settings
            warning(warningstate1)
            warning(warningstate2)
        else % ACTCNT == 0
            output.iterations = iterations;
            return
        end
        delete_constr = 0;
    end
    
    % If we are in the Phase-1 procedure check if the slack variable
    % is zero indicating we have found a feasible starting point.
    if normalize < 0
        if X(numberOfVariables,1) < eps
            ACTIND = indepInd(ACTIND);
            output.iterations = iterations;
            return;
        end
    end
       
    % Update constraints
    cstr = A*X-B;
    cstr(eqix) = abs(cstr(eqix));
    if max(cstr) > 1e5 * errnorm
        if max(cstr) > norm(X) * errnorm
            % Display a message to the command window
            if exitflag == 1 && verbosity > 0
                disp('The problem is badly conditioned; the solution may not be reliable.');
            end
        end
        how='unreliable';
    end

    %----Add blocking constraint to working set----
    
    if ind % Hit a constraint
        aix(ind)=1;
        CIND = length(ACTIND) + 1;
        ACTSET(CIND,:)=A(ind,:);
        ACTIND(CIND)=ind;
        [m,n]=size(ACTSET);
        [Q,R] = qrinsert(Q,R,CIND,A(ind,:)');
        ACTCNT = length(ACTIND);
    end
    if ~simplex_iter
        % Z = null(ACTSET);
        [m,n]=size(ACTSET);
        Z = Q(:,m+1:n);
        if ACTCNT == numberOfVariables - 1, simplex_iter = 1; end
        oldind = 0; 
    else
        % Disable the warnings about conditioning for singular and
        % nearly singular matrices
        warningstate1 = warning('off', 'MATLAB:nearlySingularMatrix');
        warningstate2 = warning('off', 'MATLAB:singularMatrix');

        %---If Simplex Alg. choose leaving constraint---
        rlambda = -R\(Q'*gf);

        % Restore the warning states to their original settings
        warning(warningstate1)
        warning(warningstate2)
       
        if isinf(rlambda(1)) && rlambda(1) < 0 
            fprintf('         Working set is singular; results may still be reliable.\n');
            [m,n] = size(ACTSET);
            rlambda = -(ACTSET + sqrt(eps)*randn(m,n))'\gf;
        end
        actlambda = rlambda;
        actlambda(eqix)=abs(actlambda(eqix));
        indlam = find(actlambda<0);
        if length(indlam)
            if STEPMIN > errnorm
                % If there is no chance of cycling then pick the constraint 
                % which causes the biggest reduction in the cost function. 
                % i.e the constraint with the most negative Lagrangian 
                % multiplier. Since the constraints are normalized this may 
                % result in less iterations.
                [minl,lind] = min(actlambda);
            else
                % Bland's rule for anti-cycling: if there is more than one 
                % negative Lagrangian multiplier then delete the constraint
                % with the smallest index in the active set.
                lind = find(ACTIND == min(ACTIND(indlam)));
            end
            lind = lind(1);
            ACTSET(lind,:) = [];
            aix(ACTIND(lind)) = 0;
            [Q,R]=qrdelete(Q,R,lind);
            Z = Q(:,numberOfVariables);
            oldind = ACTIND(lind);
            ACTIND(lind) = [];
            ACTCNT = length(ACTIND);
        else
            lambda(indepInd(ACTIND))= normf * (rlambda./normA(ACTIND));
            ACTIND = indepInd(ACTIND);
            output.iterations = iterations;
            return
        end
    end %if ACTCNT<numberOfVariables
    
    %----------Compute Search Direction-------------      
    
    if (is_qp)
        Zgf = Z'*gf; 
        if ~isempty(Zgf) && (norm(Zgf) < 1e-15)
            SD = zeros(numberOfVariables,1); 
            dirType = ZeroStep;
        else
            [SD, dirType] = compdir_mm(Z,H,gf,numberOfVariables,f);
        end
    elseif (LLS)
        Zgf = Z'*gf;
        HZ = H*Z;
        if (norm(Zgf) < 1e-15)
            SD = zeros(numberOfVariables,1);
            dirType = ZeroStep;
        else
            HXf=H*X-f;
            gf=H'*(HXf);
            [mm,nn]=size(HZ);
            if mm >= nn
                [QHZ, RHZ] =  qr(HZ,0);
                Pd = QHZ'*HXf;
                % SD = - Z*(RHZ(1:nn, 1:nn) \ Pd(1:nn,:));
                % Now need to check which is dependent
                if min(size(RHZ))==1 % Make sure RHZ isn't a vector
                    depInd = find( abs(RHZ(1,1)) < tolDep);
                else
                    depInd = find( abs(diag(RHZ)) < tolDep );
                end  
            end
            if mm >= nn && isempty(depInd) % Newton step
                % Disable the warnings about conditioning for singular and
                % nearly singular matrices
                warningstate1 = warning('off', 'MATLAB:nearlySingularMatrix');
                warningstate2 = warning('off', 'MATLAB:singularMatrix');
                SD = - Z*(RHZ(1:nn, 1:nn) \ Pd(1:nn,:));
                % Restore the warning states to their original settings
                warning(warningstate1)
                warning(warningstate2)
                dirType = NewtonStep;
            else % steepest descent direction
                SD = -Z*(Z'*gf);
                dirType = SteepDescent;
            end
        end
    else % LP
        if ~simplex_iter
            SD = -Z*(Z'*gf);
            gradsd = norm(SD);
        else
            gradsd = Z'*gf;
            if  gradsd > 0
                SD = -Z;
            else
                SD = Z;
            end
        end
        if abs(gradsd) < 1e-10 % Search direction null
            % Check whether any constraints can be deleted from active set.
            % rlambda = -ACTSET'\gf;
            if ~oldind
                % Disable the warnings about conditioning for singular and
                % nearly singular matrices
                warningstate1 = warning('off', 'MATLAB:nearlySingularMatrix');
                warningstate2 = warning('off', 'MATLAB:singularMatrix');
                rlambda = -R\(Q'*gf);
                % Restore the warning states to their original settings
                warning(warningstate1)
                warning(warningstate2)
                ACTINDtmp = ACTIND; Qtmp = Q; Rtmp = R;
            else
                % Reinsert just deleted constraint.
                ACTINDtmp = ACTIND;
                ACTINDtmp(lind+1:ACTCNT+1) = ACTIND(lind:ACTCNT);
                ACTINDtmp(lind) = oldind;
                [Qtmp,Rtmp] = qrinsert(Q,R,lind,A(oldind,:)');
            end
            actlambda = rlambda;
            actlambda(1:neqcstr) = abs(actlambda(1:neqcstr));
            indlam = find(actlambda < errnorm);
            lambda(indepInd(ACTINDtmp)) = normf * (rlambda./normA(ACTINDtmp));
            if ~length(indlam)
                ACTIND = indepInd(ACTIND);
                output.iterations = iterations;
                return
            end
            cindmax = length(indlam);
            cindcnt = 0;
            m = length(ACTINDtmp);
            while (abs(gradsd) < 1e-10) && (cindcnt < cindmax)
                cindcnt = cindcnt + 1;
                lind = indlam(cindcnt);
                [Q,R]=qrdelete(Qtmp,Rtmp,lind);
                Z = Q(:,m:numberOfVariables);
                if m ~= numberOfVariables
                    SD = -Z*Z'*gf;
                    gradsd = norm(SD);
                else
                    gradsd = Z'*gf;
                    if  gradsd > 0
                        SD = -Z;
                    else
                        SD = Z;
                    end
                end
            end
            if abs(gradsd) < 1e-10  % Search direction still null
                ACTIND = indepInd(ACTIND);
                output.iterations = iterations;
                return;
            else
                ACTIND = ACTINDtmp;
                ACTIND(lind) = [];
                aix = zeros(ncstr,1);
                aix(ACTIND) = 1;
                ACTCNT = length(ACTIND);
                ACTSET = A(ACTIND,:);
            end
            lambda = zeros(ncstr,1);
        end
    end % if is_qp
end % while 

if iterations >= maxiter
    exitflag = 0;
    how = 'MaxSQPIter';
    msg = ...
        sprintf(['Maximum number of iterations exceeded; increase options.MaxIter.\n' ...
                 'To continue solving the problem with the current solution as the\n' ...
                 'starting point, set x0 = x before calling quadprog.']);
    if verbosity > 0
      disp(msg)
    end
end

output.iterations = iterations;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function [Q,R,A,B,X,Z,how,ACTSET,ACTIND,ACTCNT,aix,eqix,neqcstr, ...
        ncstr,remove,exitflag,msg]= ...
    eqnsolv(A,B,eqix,neqcstr,ncstr,numberOfVariables,LLS,H,X,f,normf, ...
    normA,verbosity,aix,ACTSET,ACTIND,ACTCNT,how,exitflag)
% EQNSOLV Helper function for QPSUB.
%    Checks whether the working set is linearly independent and
%    finds a feasible point with respect to the working set constraints.
%    If the equalities are dependent but not consistent, warning
%    messages are given. If the equalities are dependent but consistent, 
%    the redundant constraints are removed and the corresponding variables 
%    adjusted.

% set tolerances
tolDep = 100*numberOfVariables*eps;      
tolCons = 1e-10;

Z=[]; remove =[];
msg = []; % will be given a value only if appropriate

% First see if the equality constraints form a consistent system.
[Qa,Ra,Ea]=qr(A(eqix,:));

% Form vector of dependent indices.
if min(size(Ra))==1 % Make sure Ra isn't a vector
    depInd = find( abs(Ra(1,1)) < tolDep);
else
    depInd = find( abs(diag(Ra)) < tolDep );
end
if neqcstr > numberOfVariables
    depInd = [depInd; ((numberOfVariables+1):neqcstr)'];
end      

if ~isempty(depInd)    % equality constraints are dependent
    msg = sprintf('The equality constraints are dependent.');
    how='dependent';
    exitflag = 1;
    bdepInd =  abs(Qa(:,depInd)'*B(eqix)) >= tolDep ;
        
    if any( bdepInd ) % Not consistent
        how='infeasible';   
        exitflag = -2;
        msg = sprintf('%s\nThe system of equality constraints is not consistent.',msg);
        if ncstr > neqcstr
            msg = sprintf('%s\nThe inequality constraints may or may not be satisfied.',msg);
        end
        msg = sprintf('%s\nThere is no feasible solution.',msg);
    else % the equality constraints are consistent
        % Delete the redundant constraints
        % By QR factoring the transpose, we see which columns of A'
        %   (rows of A) move to the end
        [Qat,Rat,Eat]=qr(A(eqix,:)');        
        [i,j] = find(Eat); % Eat permutes the columns of A' (rows of A)
        remove = i(depInd);
        numDepend = nnz(remove);
        if verbosity > 0
            disp('The system of equality constraints is consistent. Removing');
            disp('the following dependent constraints before continuing:');
            disp(remove)
        end
        A(eqix(remove),:)=[];
        % Even though B is a vector, we use two-index syntax when
        % removing elements so that, if all constraints end up being removed,
        % it will have size 0-by-1, and be commensurate with the empty
        %, 0-by-1 matrix A. Similarly with the active set Boolean indicator aix.
        B(eqix(remove),:)=[];
        neqcstr = neqcstr - numDepend;
        ncstr = ncstr - numDepend;
        eqix = 1:neqcstr;
        aix(remove,:) = [];
        ACTIND(1:numDepend) = [];
        ACTIND = ACTIND - numDepend;      
        ACTSET = A(ACTIND,:);
        ACTCNT = ACTCNT - numDepend;
    end % consistency check
end % dependency check
if verbosity > 0
  disp(msg)
end

% Now that we have done all we can to make the equality constraints
% consistent and independent we will check the inequality constraints
% in the working set.  First we want to make sure that the number of 
% constraints in the working set is only greater than or equal to the
% number of variables if the number of (non-redundant) equality 
% constraints is greater than or equal to the number of variables.
if ACTCNT >= numberOfVariables
    ACTCNT = max(neqcstr, numberOfVariables-1);
    ACTIND = ACTIND(1:ACTCNT);
    ACTSET = A(ACTIND,:);
    aix = zeros(ncstr,1);
    aix(ACTIND) = 1;
end

% Now check to see that all the constraints in the working set are
% linearly independent.
if ACTCNT > neqcstr
    [Qat,Rat,Eat]=qr(ACTSET');
    
    % Form vector of dependent indices.
    if min(size(Rat))==1 % Make sure Rat isn't a vector
        depInd = find( abs(Rat(1,1)) < tolDep);
    else
        depInd = find( abs(diag(Rat)) < tolDep );
    end
    
    if ~isempty(depInd)
        [i,j] = find(Eat); % Eat permutes the columns of A' (rows of A)
        remove2 = i(depInd);
        removeEq   = remove2(find(remove2 <= neqcstr));
        removeIneq = remove2(find(remove2 > neqcstr));
        
        if ~isempty(removeEq)
            % Just take equalities as initial working set.
            ACTIND = 1:neqcstr; 
        else
            % Remove dependent inequality constraints.
            ACTIND(removeIneq) = [];
        end
        aix = zeros(ncstr,1);
        aix(ACTIND) = 1;
        ACTSET = A(ACTIND,:);
        ACTCNT = length(ACTIND);
    end  
end

[Q,R]=qr(ACTSET');
Z = Q(:,ACTCNT+1:numberOfVariables);

% Disable the warnings about conditioning for singular and
% nearly singular matrices
warningstate1 = warning('off', 'MATLAB:nearlySingularMatrix');
warningstate2 = warning('off', 'MATLAB:singularMatrix');

if ~strcmp(how,'infeasible') && ACTCNT > 0
    % Find point closest to the given initial X which satisfies
    % working set constraints.
    minnormstep = Q(:,1:ACTCNT) * ...
        ((R(1:ACTCNT,1:ACTCNT)') \ (B(ACTIND) - ACTSET*X));
    X = X + minnormstep; 
    % Sometimes the "basic" solution satisfies Aeq*x= Beq 
    % and A*X < B better than the minnorm solution. Choose the one
    % that the minimizes the max constraint violation.
    err = A*X - B;
    err(eqix) = abs(err(eqix));
    if any(err > eps)
        Xbasic = ACTSET\B(ACTIND);
        errbasic = A*Xbasic - B;
        errbasic(eqix) = abs(errbasic(eqix));
        if max(errbasic) < max(err) 
            X = Xbasic;
        end
    end
end

% Restore the warning states to their original settings
warning(warningstate1)
warning(warningstate2)

% End of eqnsolv.m







