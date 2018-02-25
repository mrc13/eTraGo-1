"""line extendables functions"""
import numpy as np
from numpy import genfromtxt
np.random.seed()
import time
from math import sqrt
import os
import pandas as pd
if not 'READTHEDOCS' in os.environ:
    from tools.io import NetworkScenario, results_to_oedb
    from tools.plot import (plot_line_loading, plot_stacked_gen,add_coordinates,
                            curtailment, gen_dist, storage_distribution,
                            plot_max_line_loading, plot_max_opt_line_loading,
                            plot_max_opt_line_loading_bench,transformers_distribution,
                            plot_dif_line_MW,plot_dif_line_percent)
    from tools.utilities import (oedb_session, load_shedding, data_manipulation_sh,
                                 results_to_csv, parallelisation, pf_post_lopf,
                                 loading_minimization, calc_line_losses,
                                 group_parallel_lines)
    from cluster.networkclustering import (busmap_from_psql, cluster_on_extra_high_voltage,
                                           kmean_clustering)
    from etrago.cluster.snapshot import snapshot_clustering, daily_bounds

    #from appl import etrago                                       
#import csv
# toDo reduce import

def annualized_costs(cc,t,i):
     """
     This function calculates the Equivalent Annual Cost of an project.
     
     ########################### input parameters ###########################
 
     cc: Capital Cost (Overnight)
     t: Lifetime of the project / investment.
     i: Interest rate of the project / investment.
 
     ########################### output parameters ##########################
     EAC : The function return the Equivalent Annual Cost of the project.
      
     """
     EAC = cc * (i/(1-1/(1+i)**t))
     
     return EAC


def capacity_factor(network,cap_fac):
    """
    This function is for changing the capacities of lines and
    transformers.

    ########################### input parameters ###########################

    network: The whole network, which are to calculate
    cap_fac: cap_fac is a variable for the capacitiy factor.

    ########################### output parameters ##########################
    network : The function return the network with new capacities of lines
              and transformers

    """


    network.lines.s_nom = network.lines.s_nom * cap_fac
    network.transformers.s_nom = network.transformers.s_nom * cap_fac

    return network


def extend_all_lines(network):
    
    """
    This functions set all the lines to be extendable. (Case1&2:benchmark)
    This function was created to compare the performance of the simulation 
    by doing just 1LOPF setting all lines extandable
    
    ########################### input parameters ###########################

    network: The whole network, which are to calculate

    ########################### output parameters ##########################

    network: The whole network, after all lines are set as extendable
    
    """
    
    network.lines.s_nom_extendable = True
    network.lines.s_nom_min = network.lines.s_nom
    network.lines.s_nom_max = np.inf
    
    return network

def extend_all_trafos(network):
    
    """
    This functions set all the trafos to be extendable. (Case1&2:benchmark)
    This function was created to compare the performance of the simulation 
    by doing just 1LOPF setting all trafos extandable
    
    ########################### input parameters ###########################

    network: The whole network, which are to calculate

    ########################### output parameters ##########################

    network: The whole network, after all lines are set as extendable
    
    """
    
    network.transformers.s_nom_extendable = True
    network.transformers.s_nom_min = network.transformers.s_nom
    network.transformers.s_nom_max = np.inf
    
    return network

def overload_lines(network):

    """
    This function is for finding the overload lines.
    First the loadings of all lines would calculate for each timestep.
    Seconde the maximum loadings of all lines are setting.
    After that it will check the value. If the value is over 100% the line
    will be consider. After finding all lines it will be found the timesteps
    of the maximum loading of the lines which are considered.
    Last the timesteps which are the same will be counted and sorted by the
    greatest number.

    ########################### input parameters ###########################

    network: The whole network, which are to calculate

    ########################### output parameters ##########################
    The function return the maximum loadings of each line (max_loading) and
    the timesteps which are count in (time_list).

    """

    # List for counting the maximum value for timesteps
    # 0 : line keys
    # 1 : maximum loadings of each line
    # 2 : timestep of maximum loading
    max_loading = [[],[],[]]

    # List for counting the maximum loadings of each timestep
    # 0 : timestep index of line
    # 1 : Number of maximum loadings
    timesteps = [[],[]]

    # The same list like timesteps but for sorting by maximum number of loadings
    time_list =[]

    i=0
    while (i<len(network.lines_t.p0.keys())):
        # set current line key
        max_loading[0].append(network.lines_t.p0.keys()[i])

        # set maximum loading of the current line
        if(network.lines_t.q0.empty):
            s_current = abs(network.lines_t.p0[max_loading[0][i]])
        else:
            p = network.lines_t.p0[max_loading[0][i]]
            q = network.lines_t.q0[max_loading[0][i]]
            s_current = sqrt(p**2+q**2)

        max_loading[1].append(max(abs(s_current)/network.lines.s_nom[max_loading[0][i]]*100))

        # Find the timestep of maximum loading
        x= 0
        while(x<len(s_current)):
            if(s_current[x]==(max(abs(s_current)))):
                # set the timestep of maximum loading
                max_loading[2].append(x)
                break
            else:
                x+=1

        # filtering the lines which has a loading of over 100%
        loading = max_loading[1][i]
        time_index = max_loading[2][i]

        if (((time_index in timesteps[0]) == True) and (loading >= 100)):
            index = timesteps[0].index(time_index)
            timesteps[1][index] +=1
        elif(loading >= 100):
            timesteps[0].append(time_index)
            timesteps[1].append(1)

        i+=1

    # save the Result in a other way
    x=0
    while(x<len(timesteps[0])):
        time_list.append([timesteps[0][x],timesteps[1][x]])
        x+=1

    # For sorting the List by the item 1
    def getKey(item):
                return item[1]

    print('max loading = ', max_loading)
    print('Time steps = ', timesteps)
    print('time list unsorted= ', time_list)

    time_list = sorted(time_list,key=getKey)
    
 
    print('time list sorted= ', time_list)

    return max_loading,time_list

def overload_trafo(network):

    """
    This function is for finding the overload transformators.
    First the loadings of all transformators would calculate for each
    timestep.
    Seconde the maximum loadings of all lines are setting.
    After that it will check the value. If the value is over 100% the line
    will be consider. After finding all lines it will be found the timesteps
    of the maximum loading of the transformators which are considered.
    Last the timesteps which are the same will be counted and sorted by the
    greatest number.

    ########################### input parameters ###########################

    network: The whole network, which are to calculate

    ########################### output parameters ##########################
    The function return the maximum loadings of each transformators
    (max_loading) and the timesteps which are count in (time_list).

    """

    # List for counting the maximum value for timesteps
    # 0 : trafo keys
    # 1 : maximum loadings of each trafo
    # 2 : timestep of maximum loading
    max_loading = [[],[],[]]

    # List for counting the maximum loadings of each timestep
    # 0 : timestep index of trafo
    # 1 : Number of maximum loadings
    timesteps = [[],[]]

    # The same list like timesteps but for sorting by maximum number of loadings
    time_list =[]

    i=0
    while (i<len(network.transformers_t.p0.keys())):
        # set current trafo key
        max_loading[0].append(network.transformers_t.p0.keys()[i])

        # set maximum loading of the current trafo
        if(network.transformers_t.q0.empty):
            s_current = abs(network.transformers_t.p0[max_loading[0][i]])
        else:
            p = network.transformers_t.p0[max_loading[0][i]]
            q = network.transformers_t.q0[max_loading[0][i]]
            s_current = sqrt(p**2+q**2)

        max_loading[1].append(max(abs(s_current)/network.transformers.s_nom[max_loading[0][i]]*100))

        # Find the timestep of maximum loading
        x= 0
        while(x<len(s_current)):
            if(s_current[x]==(max(abs(s_current)))):
                # set the timestep of maximum loading
                max_loading[2].append(x)
                break
            else:
                x+=1

        # filtering the trafo which has a loading of over 100%
        loading = max_loading[1][i]
        time_index = max_loading[2][i]

        if (((time_index in timesteps[0]) == True) and (loading >= 100)):
            index = timesteps[0].index(time_index)
            timesteps[1][index] +=1
        elif(loading >= 100):
            timesteps[0].append(time_index)
            timesteps[1].append(1)

        i+=1

    # save the Result in a other way
    x=0
    while(x<len(timesteps[0])):
        time_list.append([timesteps[0][x],timesteps[1][x]])
        x+=1

    # For sorting the List by the item 1
    def getKey(item):
                return item[1]

    time_list = sorted(time_list,key=getKey)
    
    print('timesteps tx', timesteps)
    print('time list tx', time_list)

    return max_loading,time_list


def set_line_cost(network,time_list,max_loading,cost_1,cost_2,cost_3):
    """
    This function set the capital cost of lines which ar extendable.
    This function set at the same time that the choosen lines are extendable
    for the calculation.

    ########################### input parameters ###########################

    network: The whole network, which are to calculate.
    time_list : List whith all timesteps which are considering for the
                calculation.
    max_loading: List with all maximum loadings of each line.
                 Index 0 : line keys
                 Index 1 : maximum loadings of each line
                 Index 2 : timestep of maximum loading

    cost_1 : The capital cost for extendable 110kV-lines
    cost_2 : The capital cost for extendable 220kV-lines
    cost_3 : The capital cost for extendable 380kV-lines

    ########################### output parameters ##########################
    The function return the network. In this variable the capital costs of
    the lines which are concidered are setted.
    It return also to extra lists.
    line_time: List with all timesteps which are considered.
    all_time: is the same list, but is for adding another datas.

    """

    #save the result in differnt variables
    lines_time=[]
    all_time = []

    i = 0
    while(i<len(time_list)):
#        if(i > 0.1*(args['end_h']-args['start_h'])):
#                break
        lines_time.append(time_list[len(time_list)-1-i][0])
        all_time.append(time_list[len(time_list)-1-i][0])
        
        print ('lines_time', lines_time)
        
        index = [a for a,u in enumerate(max_loading[2]) if u==lines_time[i]]

        print('index', index)

        for k in index:
            print('k= ', k)
            if(max_loading[1][k]>100):
                network.lines.s_nom_extendable[max_loading[0][k]] = True
                network.lines.s_nom_min[max_loading[0][k]] = network.lines.s_nom[max_loading[0][k]]
                network.lines.s_nom_max[max_loading[0][k]] = np.inf

                name_bus_0 = network.lines.bus0[max_loading[0][k]]
                name_bus_1 = network.lines.bus1[max_loading[0][k]]

                U_bus_0 = network.buses.v_nom[name_bus_0]
                U_bus_1 = network.buses.v_nom[name_bus_1]

                if(U_bus_0 == U_bus_1):
                    if(U_bus_0 == 110):
                        cc0 = cost_1
                        #network.lines.capital_cost[max_loading[0][k]] = \
                        #    (cost_1*network.lines.length[max_loading[0][k]]/network.lines.s_nom[max_loading[0][k]])/\
                        #    (90*8760)
                    elif(U_bus_0 == 220):
                        cc0 = cost_2
                        #network.lines.capital_cost[max_loading[0][k]] = \
                        #    (cost_2*network.lines.length[max_loading[0][k]]/network.lines.s_nom[max_loading[0][k]])/\
                        #    (90*8760)
                    else:
                        cc0 = cost_3
                        #network.lines.capital_cost[max_loading[0][k]] = \
                        #    (cost_3*network.lines.length[max_loading[0][k]]/network.lines.s_nom[max_loading[0][k]])/\
                        #    (90*8760)
                    cc1 = (cc0*network.lines.length[max_loading[0][k]])
                    maxload1 = network.lines.s_nom[max_loading[0][k]] * ((max_loading[1][k])/100)
                    cc = cc1/maxload1
                    network.lines.capital_cost[max_loading[0][k]] = annualized_costs(cc,40,0.05)
                    print('cc1= ', cc1)
                    print('maxload1= ', maxload1)
                
                else:
                    print('Error')
                    
                print('cap costs =', network.lines.capital_cost[max_loading[0][k]])
            else:  # Delete else, just for the print function
                    print('No excecute in k= ', k)
        i+=1

    return network,lines_time,all_time


def set_line_cost_BM(network,cost_1,cost_2,cost_3):
    
    i=0
    while(i<len(network.lines)):
        name_bus_0 = network.lines.bus0[i]
        name_bus_1 = network.lines.bus1[i]

        U_bus_0 = network.buses.v_nom[name_bus_0]
        U_bus_1 = network.buses.v_nom[name_bus_1]

        if(U_bus_0 == U_bus_1):
            if(U_bus_0 == 110):
                cc0 = cost_1
                #network.lines.capital_cost[max_loading[0][k]] = \
                #    (cost_1*network.lines.length[max_loading[0][k]]/network.lines.s_nom[max_loading[0][k]])/\
                #    (90*8760)
            elif(U_bus_0 == 220):
                cc0 = cost_2
                #network.lines.capital_cost[max_loading[0][k]] = \
                #    (cost_2*network.lines.length[max_loading[0][k]]/network.lines.s_nom[max_loading[0][k]])/\
                #    (90*8760)
            else:
                cc0 = cost_3
                #network.lines.capital_cost[max_loading[0][k]] = \
                #    (cost_3*network.lines.length[max_loading[0][k]]/network.lines.s_nom[max_loading[0][k]])/\
                #    (90*8760)
            cc1 = (cc0*network.lines.length[i])
            maxload1 = network.lines.s_nom[i] #* ((max_loading[1][k])/100)
            cc = cc1/maxload1
            network.lines.capital_cost[i] = annualized_costs(cc,40,0.05)
            print('cc1= ', cc1)
            print('maxload1= ', maxload1)
        
        else:
            print('Error')
                    
        i+=1
            
    return network


def set_trafo_cost(network,time_list,max_loading,cost_1,cost_2,cost_3):

    """
    This function set the capital cost of transformators which ar extendable.
    This function set at the same time that the choosen transformators are
    extendable for the calculation.

    ########################### input parameters ###########################

    network: The whole network, which are to calculate.
    time_list : List whith all timesteps which are considering for the
                calculation.
    max_loading: List with all maximum loadings of each transformators.
                 Index 0 : transformators keys
                 Index 1 : maximum loadings of each transformators
                 Index 2 : timestep of maximum loading

    cost_1 : The capital cost for extendable 110kV-220kV and 110kV-380kV
             Transformators.
    cost_2 : The capital cost for extendable 220kV-380kV Transformers
    cost_3 : The capital cost for extendable Transformers (rest)

    ########################### output parameters ##########################
    The function return the network. In this variable the capital costs of
    the transformators which are concidered are setted.
    It return also to extra lists.
    trafo_time: List with all timesteps which are considered.

    """


    # List of choosen timesteps
    trafo_time=[]

    i = 0
    while(i<len(time_list)):
#        if(i > 0.1*(args['end_h']-args['start_h'])):
#            break
        trafo_time.append(time_list[len(time_list)-1-i][0])

        index = [a for a,u in enumerate(max_loading[2]) if u==trafo_time[i]]
        for k in index:
            if(max_loading[1][k]>100):
                network.transformers.s_nom_extendable[max_loading[0][k]] = True
                network.transformers.s_nom_min[max_loading[0][k]] = network.transformers.s_nom[max_loading[0][k]]
                network.transformers.s_nom_max[max_loading[0][k]] = np.inf

                name_bus_0 = network.transformers.bus0[max_loading[0][k]]
                name_bus_1 = network.transformers.bus1[max_loading[0][k]]

                U_bus_0 = network.buses.v_nom[name_bus_0]
                U_bus_1 = network.buses.v_nom[name_bus_1]

                U_OS = max(U_bus_0,U_bus_1)
                U_US = min(U_bus_0,U_bus_1)

                if((U_OS == 220 and U_US == 110) or (U_OS == 380 and U_US == 110)):
                    network.transformers.capital_cost[max_loading[0][k]] = \
                        ((cost_1)/(40*8760))
                elif(U_OS == 380 and U_US == 220):
                    network.transformers.capital_cost[max_loading[0][k]] = \
                        ((cost_2)/(40*8760))
                else:
                    network.transformers.capital_cost[max_loading[0][k]] = \
                        ((cost_3)/(40*8760))
                    print('Other Transformator' + str(k))

        i+=1

    return network,trafo_time


def line_extendable(network, args, scenario):
    """
    Function which prepare and run a
    line_extendable calculation.

    """  
    
    print("Lines_extendable_S_ini",network.lines.s_nom)
    print("Lines_extendable_S_ini_opt",network.lines.s_nom_opt)
   # set the capacity-factory for the first lopf
    cap_fac = 1.3
         
    # Change the capcity of lines and transformers
    network = capacity_factor(network,cap_fac)
                                        
    ######################## Set all lines extendable ##############
    
    #network = extend_all_lines(network)
    
    
    #print("Lines_extendable_S_ini_ext",network.lines.s_nom_extendable)
    #print("Lines_extendable_S_ini_min",network.lines.s_nom_min)
    #print("Lines_extendable_S_ini_max",network.lines.s_nom_max)
    
    ############################ 1. Lopf ###########################
    
    print ('bf 1st LOPF snapshots', len(network.snapshots))
    
    last_snapshot = len(network.snapshots)  
    x = time.time()
    #network.lopf(network.snapshots, solver_name=args['solver']) 
    
    parallelisation(network, start_snapshot=1, \
        end_snapshot= last_snapshot ,group_size=1, solver_name=args['solver'])
    
    #parallelisation(network, start_snapshot=args['start_snapshot'], \
    #    end_snapshot=args['end_snapshot'],group_size=1, solver_name=args['solver'])
    
    y = time.time()
    print('time 1st lopf= ', y-x) 
    z = y -x
    z= pd.Series(data=z)
    z.to_csv(path='/home/felipe/Uniproject/test123.csv')
    z.to_frame()
    z.plot()
    z.index
    #z.index='runtime 2nd lopf'
    
    print('results after 1stLOPF', network.lines_t.p0 )
    
    # return to original capacities
    network = capacity_factor(network,(1/cap_fac))
        
        
    # plotting the loadings of lines at start
    plot_max_line_loading(network,filename = 'Start_maximum_line_loading.png')
         
         
    ############################ Analyse ############################
         
    # Finding the overload lines and timesteps
    maximum_line_loading,line_time_list = overload_lines(network)
         
    # Finding the overload transformers and timestep
    maximum_trafo_loading,trafo_time_list = overload_trafo(network)
                     
    ####################### Set capital cost ########################
         
    # Set capital cost for extendable lines
    cost_1 = 6.0000 # 110kV extendable
    cost_2 = 1.600000/2 # 220kV extendable
    cost_3 = 2.00000 # 380kV extendable
        
    network,lines_time,all_time = set_line_cost(network,\
                                                line_time_list,\
                                                maximum_line_loading,\
                                                cost_1,\
                                                cost_2,\
                                                cost_3)
         
         
    # Set capital cost for extendable trafo
    cost_1 = 5200000/300 # 220/110kV or 380/110kV extendable
    cost_2 = 8500000/600# 380/220kV extendable
    cost_3 = 8500000/600 # other extendable
         
    network,trafo_time = set_trafo_cost(network,\
                                        trafo_time_list,\
                                        maximum_trafo_loading,\
                                        cost_1,\
                                        cost_2,\
                                        cost_3)
        
         
    ####################### Set all timesteps #######################
    
    all_time.sort() 
    i=0
    while(i<len(trafo_time)):
        if((trafo_time[i] in all_time) == True):
            i+=1
        else:
            all_time.append(trafo_time[i])
            i+=1
            
    ######################### calc 2. Lopf ##########################

    print('all time pre1', all_time)
    length_time = len(all_time)
    if(length_time==0):
        timeindex = scenario.timeindex
      
    network.lines.capital_cost =\
                                network.lines.capital_cost * length_time

    network.transformers.capital_cost =\
                         network.transformers.capital_cost * length_time
    
    all_time.sort()
    print('Snapshots len0', len(network.snapshots))
    print('Snapshots 0', network.snapshots)
    print('all time pre2', all_time)
   
    """
    i=0
    while(i<len(all_time)):
        if i==0:
            timeindex = network.snapshots[all_time[i]:all_time[i]+1]
        else:
            timeindex =pd.DatetimeIndex.append(timeindex,\
                      other=network.snapshots[all_time[i]:all_time[i]+1])
        i+=1
    print('timeindex=',timeindex )
    """
 
    ##Method for 2nd LOPF
    x = time.time()
    network.lopf(network.snapshots, solver_name=args['solver'])  
    y = time.time()
    #print('results after 2ndLOPF', network.lines_t.p0 )
    print('time 2nd lopf= ', y-x)                          
    print("Lines_extendable_S_fin",network.lines.s_nom)
    print("Lines_extendable_S_fin_opt",network.lines.s_nom_opt)
    print("Lines_extendable_S_fin_ext",network.lines.s_nom_extendable)
    ##################### Plotting the Results #####################
    #if len(lines_time) >0:
    
        #plot_max_opt_line_loading(network,lines_time,\
        #                              filename='maximum_optimal_lines.png')
    #else:
        #print("No expansions required", len(lines_time))
    storage_distribution(network)
    
    return network

def line_extendableBM(network, args, scenario):
    
    """
    Function which prepare and run a
    line_extendable calculation.

    """  
    print("Lines_extendable_S_ini0_ext",network.lines.s_nom_extendable)
    
    network = extend_all_lines(network)
    
    network = extend_all_trafos(network)
    
    print("Lines_extendable_S_ini",network.lines.s_nom)
    print("Lines_extendable_S_ini_ext",network.lines.s_nom_extendable)
    
    ####################### Set capital cost ########################
         
    # Set capital cost for extendable lines
    cost_1 = 60000 # 110kV extendable
    cost_2 = 1600000/2 # 220kV extendable
    cost_3 = 200000 # 380kV extendable
    
    network = set_line_cost_BM(network,cost_1,cost_2,cost_3)
    

    x = time.time()
    print('time xx = ', x) 
    network.lopf(network.snapshots, solver_name=args['solver'])  
    y = time.time()
    
    print('time unique lopf= ', y-x)                          
    print("Lines_extendable_S_fin",network.lines.s_nom)
    print("Lines_extendable_S_fin_ext",network.lines.s_nom_extendable)
    
    
    return network