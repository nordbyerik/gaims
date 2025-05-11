
class ActivationHook:
    """Hook to extract activations from a specific layer of a transformer model."""
    def __init__(self, model, layer_name, transformation_function=None):
        self.activations = None
        self.layer_name = layer_name
        self.transformation_function = transformation_function if transformation_function is not None else lambda x: x
        self._handle = None

        # Register forward hook
        module = self.get_layer(model, layer_name)
        if "mlp" in self.layer_name:
            self._handle = module.register_forward_hook(self.hook_mlp)
        elif "self_attn" in self.layer_name:
            self._handle = module.register_forward_hook(self.hook_attention)
        else:
            raise ValueError(f"Unsupported layer: {layer_name}")
    
    @staticmethod
    def get_layer(model, layer_name):
        layer_idx = int(layer_name.split('.')[-2])
        if "GPTNeoXForCausalLM" in model.config.architectures:
            layer = model.gpt_neox.layers[layer_idx]
        else:
            layer = model.model.layers[layer_idx]

        if 'mlp' in layer_name:
            return layer.mlp
        elif 'self_attn' in layer_name:
            if "GPTNeoXForCausalLM" in model.config.architectures:
                return layer.attention
            else:
                return layer.self_attn
        elif 'residual' in layer_name:
            return layer
    def set_transformation_function(self, transformation_function):
        self.transformation_function = transformation_function

    def hook_mlp(self, module, input, output):
        self.activations = output.detach()
        return self.transformation_function(output)

    def hook_attention(self, module, input, output):
        self.activations = output[0].detach()
        output_updated = self.transformation_function(output[0])
        output = (output_updated,) + output[1:]
        return output

    def print_activations(self):
        print(self.activations)

    def clear_activations(self):
        self.activations = None

    def clear_transformation_function(self):
        self.transformation_function = lambda x: x

    def clear(self):
        self.clear_activations()
        self.clear_transformation_function()

    def remove(self):
        self._handle.remove()

    def to(self, device):
        self.device = device
        return self

    def __enter__(self):
        return self
    def __exit__(self):
        self.clear()
        self.remove()