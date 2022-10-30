
# In[ ]:


"""Implement a minimum required flow
"""
def convert_to_mrf(node,
                   mrf = 5):
    
    def pull_check_mrf(node,vqip = None):
        #Respond to a pull check to the node
        
        #Work out how much water is available upstream
        reply = node.pull_check_basic(vqip)
        
        #Apply MRF
        reply['volume'] = max(reply['volume'] - (node.mrf - node.mrf_satisfied_this_timestep), 0)
        
        #If the pulled amount has been specified, pick the minimum of the available and that
        if vqip is not None:
            reply['volume'] = min(reply['volume'], vqip['volume'])
        
        #Return avaiable
        return reply
        
    def pull_set_mrf(node, vqip):
        #Respond to a pull request to the node
        
        #Copy the request for boring reasons
        request = node.copy_vqip(vqip)
        
        #Increase the request by the amount of MRF not yet satisfied
        request['volume'] += (node.mrf - node.mrf_satisfied_this_timestep)
        
        #Pull the new updated request from upstream nodes
        reply = node.pull_distributed(request)
        
        #First satisfy the MRF
        reply_to_mrf = min((node.mrf - node.mrf_satisfied_this_timestep), reply['volume'])
        node.mrf_satisfied_this_timestep += reply_to_mrf
        
        reply_to_mrf = node.v_change_vqip(reply, reply_to_mrf)
        
        #Update reply (less the amount for MRF)
        reply = node.extract_vqip(reply, reply_to_mrf)
        
        #Then route that water downstream so it is not available
        mrf_route_reply = node.push_distributed(reply_to_mrf, of_type = ['Node'])
        if mrf_route_reply['volume'] > constants.FLOAT_ACCURACY:
            print('warning MRF not able to push')
            
        #Return pulled amount
        return reply
    
    def end_timestep(node):
        #Update MRF satisfied
        node.mrf_satisfied_this_timestep = 0
    
    #Initialise MRF variables
    node.mrf = mrf
    node.mrf_satisfied_this_timestep = 0
    
    #Change pull functions to the ones defined above
    node.pull_set_handler['default'] = lambda x : pull_set_mrf(node, x)
    node.pull_check_handler['default'] = lambda x : pull_check_mrf(node, x)
    
    #Change end timestep function to one defined above
    node.end_timestep = lambda : end_timestep(node)

#Convert the abstraction node to apply an MRF
convert_to_mrf(farmoor_abstraction, mrf = 1.5 * constants.M3_S_TO_M3_DT)


# In[ ]:


#Reinitialise and rerun
my_model.reinit()
flows_mrf, tanks_mrf, _, _ = my_model.run()

flows_mrf = pd.DataFrame(flows_mrf)
tanks = pd.DataFrame(tanks)
tanks_mrf = pd.DataFrame(tanks_mrf)

# In[ ]:


"""Compare before and after
"""
f, axs = plt.subplots(3,1)
axs[0].plot(flows.groupby('arc').get_group('farmoor_to_mixer').set_index('time').flow,label = 'original')
axs[0].plot(flows_mrf.groupby('arc').get_group('farmoor_to_mixer').set_index('time').flow,label = 'mrf')
axs[0].legend()

axs[1].plot(flows.groupby('arc').get_group('abstraction_to_farmoor').set_index('time').flow,label = 'original')
axs[1].plot(flows_mrf.groupby('arc').get_group('abstraction_to_farmoor').set_index('time').flow,label = 'mrf')
axs[1].legend()

axs[2].plot(tanks.groupby('node').get_group('farmoor').set_index('time').storage,label = 'original')
axs[2].plot(tanks_mrf.groupby('node').get_group('farmoor').set_index('time').storage,label = 'mrf')
axs[2].legend()



