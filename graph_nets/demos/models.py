# Copyright 2018 The GraphNets Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or  implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Model architectures for the demos."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from graph_nets import modules
from graph_nets import utils_tf
import sonnet as snt

NUM_LAYERS = 2  # Hard-code number of layers in the edge/node/global models.
LATENT_SIZE = 16  # Hard-code latent layer sizes for demos.

def make_softmax_model():
    return snt.Sequential([
            snt.nets.MLP([64,32,2],activate_final=Ture),
        ])
def make_mlp_model():
  """Instantiates a new MLP, followed by LayerNorm.

  The parameters of each new MLP are not shared with others generated by
  this function.

  Returns:
    A Sonnet module which contains the MLP and LayerNorm.
  """
  return snt.Sequential([
      snt.nets.MLP([LATENT_SIZE] * NUM_LAYERS, activate_final=True),
      snt.LayerNorm()
  ])

def make_edge_model():
  return snt.Sequential([
    snt.nets.MLP([64,32,3],activate_final=True),
#    snt.LayerNorm()
  ])

def make_node_model():
  return snt.Sequential([
    snt.nets.MLP([256],activate_final=True),
    snt.LayerNorm()
  ])

#def make_node_model1():
#  return snt.Sequential([
#    snt.nets.MLP([256],activate_final=False),
#    snt.LayerNorm()
#  ])

def make_Hnode_model():
  return snt.Sequential([
    snt.nets.MLP([64],activate_final=True),
    snt.LayerNorm()
  ])

def make_Lnode_model():
  return snt.Sequential([
    snt.nets.MLP([64,32],activate_final=True),
    snt.LayerNorm()
  ])

def make_conv_model():
  """Instantiates a new MLP, followed by LayerNorm.

  The parameters of each new MLP are not shared with others generated by
  this function.

  Returns:
    A Sonnet module which contains the MLP and LayerNorm.
  """
  return snt.Sequential([
      snt.nets.ConvNet2D(output_channels=[32,32],kernel_shapes=[3,3],strides=[1,1],paddings=['VALID','VALID'],activate_final=True),
      snt.BatchFlatten(),
      
      snt.nets.MLP([256], activate_final=True),
      # snt.nets.MLP([64,32], activate_final=True),
      # snt.nets.MLP([3] , activate_final=False),
      #snt.LayerNorm()
  ])

# def make_conv_model2():
#   return snt.Sequential([
#       snt.nets.ConvNet2D(output_channels=[32,32],kernel_shapes=[3,3],strides=[1,1],paddings=['VALID','VALID'],activate_final=True),
#       snt.BatchFlatten(),
#       snt.nets.MLP([256,128,64,21] , activate_final=False),
#       # snt.LayerNorm()
#   ])

def get_q_model2():
  return snt.Sequential([
    # snt.nets.ConvNet2D(output_channels=[32,32],kernel_shapes=[3,3],strides=[1,1],paddings=['VALID','VALID'],activate_final=True),
    # snt.BatchFlatten(),
    snt.nets.MLP([128,64,13],activate_final=False)
  ])
 
def get_q_model():
  return snt.Sequential([
    # snt.nets.ConvNet2D(output_channels=[32,32],kernel_shapes=[3,3],strides=[1,1],paddings=['VALID','VALID'],activate_final=True),
    # snt.BatchFlatten(),
    snt.nets.MLP([128,64,21],activate_final=False)
  ])
class MLPGraphIndependent(snt.AbstractModule):
  """GraphIndependent with MLP edge, node, and global models."""

  def __init__(self, name="MLPGraphIndependent"):
    super(MLPGraphIndependent, self).__init__(name=name)
    with self._enter_variable_scope():
      self._network = modules.GraphIndependent(
          edge_model_fn=make_mlp_model,
          node_model_fn=make_mlp_model,
          global_model_fn=make_mlp_model)

  def _build(self, inputs):
    return self._network(inputs)


class MLPGraphNetwork(snt.AbstractModule):
  """GraphNetwork with MLP edge, node, and global models."""

  def __init__(self, name="MLPGraphNetwork"):
    super(MLPGraphNetwork, self).__init__(name=name)
    with self._enter_variable_scope():
      self._network = modules.GraphNetwork(make_mlp_model, make_mlp_model,
                                           make_mlp_model)

  def _build(self, inputs):
    return self._network(inputs)


class EncodeProcessDecode(snt.AbstractModule):
  """Full encode-process-decode model.

  The model we explore includes three components:
  - An "Encoder" graph net, which independently encodes the edge, node, and
    global attributes (does not compute relations etc.).
  - A "Core" graph net, which performs N rounds of processing (message-passing)
    steps. The input to the Core is the concatenation of the Encoder's output
    and the previous output of the Core (labeled "Hidden(t)" below, where "t" is
    the processing step).
  - A "Decoder" graph net, which independently decodes the edge, node, and
    global attributes (does not compute relations etc.), on each message-passing
    step.

                      Hidden(t)   Hidden(t+1)
                         |            ^
            *---------*  |  *------*  |  *---------*
            |         |  |  |      |  |  |         |
  Input --->| Encoder |  *->| Core |--*->| Decoder |--->make_edge_model Output(t)
            |         |---->|      |     |         |
            *---------*     *------*     *---------*
  """

  def __init__(self,
               edge_output_size=None,
               node_output_size=None,
               global_output_size=None,
               name="EncodeProcessDecode"):
    super(EncodeProcessDecode, self).__init__(name=name)
    self._encoder = MLPGraphIndependent()
    self._core = MLPGraphNetwork()
    self._decoder = MLPGraphIndependent()
    # Transforms the outputs into the appropriate shapes.
    if edge_output_size is None:
      edge_fn = None
    else:
      edge_fn = lambda: snt.Linear(edge_output_size, name="edge_output")
    if node_output_size is None:
      node_fn = None
    else:
      node_fn = lambda: snt.Linear(node_output_size, name="node_output")
    if global_output_size is None:
      global_fn = None
    else:
      global_fn = lambda: snt.Linear(global_output_size, name="global_output")
    with self._enter_variable_scope():
      self._output_transform = modules.GraphIndependent(edge_fn, node_fn,
                                                        global_fn)

  def _build(self, input_op, num_processing_steps):
    latent = self._encoder(input_op)
    latent0 = latent
    output_ops = []
    for _ in range(num_processing_steps):
      core_input = utils_tf.concat([latent0, latent], axis=1)
      latent = self._core(core_input)
      decoded_op = self._decoder(latent)
      output_ops.append(self._output_transform(decoded_op))
    return output_ops
    
class GCrpNetworkTiny(snt.AbstractModule):
  """GraphNetwork with MLP edge, node, and global models."""

  def __init__(self, name="GCrpNetworkTiny"):
    super(GCrpNetworkTiny, self).__init__(name=name)
    with self._enter_variable_scope():
      self._obsEncoder=modules.obsEncoder(encoder_fn=make_conv_model)
      self._network = modules.CommNet(
          edge_model_fn=make_edge_model,
          node_model_fn=make_node_model)

      self._hnetwork=modules.HCommNet(
         edge_model_fn=make_edge_model,
          node_model_fn=make_Hnode_model)
  
      self._Lnetwork = modules.LCommNet(
          edge_model_fn=make_edge_model,
        node_model_fn=make_Lnode_model)
      self._qnet=modules.qEncoder(mlp_fn=get_q_model2)


  def _build(self, inputs):
    
    #return self._qnet(self._obsEncoder(inputs))
    return self._qnet(self._Lnetwork(self._hnetwork(self._network(self._obsEncoder(inputs)))))
    # return
class GCrpNetwork(snt.AbstractModule):
  """GraphNetwork with MLP edge, node, and global models."""

  def __init__(self, name="GCrpNetwork"):
    super(GCrpNetwork, self).__init__(name=name)
    with self._enter_variable_scope():
      self._obsEncoder=modules.obsEncoder(encoder_fn=make_conv_model)
      self._network = modules.CommNet(
          edge_model_fn=make_edge_model,
          node_model_fn=make_node_model)

      self._hnetwork=modules.HCommNet(
         edge_model_fn=make_edge_model,
          node_model_fn=make_Hnode_model)
  
      self._Lnetwork = modules.LCommNet(
          edge_model_fn=make_edge_model,
        node_model_fn=make_Lnode_model)
      self._qnet=modules.qEncoder(mlp_fn=get_q_model)


  def _build(self, inputs):
    
    #return self._qnet(self._obsEncoder(inputs))
    return self._qnet(self._Lnetwork(self._hnetwork(self._network(self._obsEncoder(inputs)))))
    # return
class HGCrpNetwork(snt.AbstractModule):
  def __init__(self, name="HGCrpNetwork"):
    super(HGCrpNetwork, self).__init__(name=name)
    with self._enter_variable_scope():
      self._obsEncoder=modules.obsEncoder(encoder_fn=make_conv_model)
      self._network = modules.CommNet(
          edge_model_fn=make_edge_model,
          node_model_fn=make_node_model)

      self._hnetwork=modules.HCommNet(
         edge_model_fn=make_edge_model,
          node_model_fn=make_Hnode_model)
  
      self._Lnetwork = modules.LCommNet2(
          edge_model_fn=make_edge_model,
        node_model_fn=make_Lnode_model)
      self._qnet=modules.qEncoder(mlp_fn=get_q_model)


  def _build(self, inputs):
    
    #return self._qnet(self._obsEncoder(inputs))
    return self._qnet(self._Lnetwork(self._network(self._obsEncoder(inputs))))
 