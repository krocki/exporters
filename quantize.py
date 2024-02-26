import coremltools as ct
import coremltools.optimize.coreml as cto

uncompressed_model_path = "./mistral-7b-instruct-v0.2-512-fp16.mlpackage"

mlmodel = ct.models.MLModel(uncompressed_model_path)
config = cto.OptimizationConfig.from_yaml("linear_config.yaml")
compressed_mlmodel = cto.linear_quantize_weights(mlmodel, config)

compressed_mlmodel.save("mistral-7b-instruct-v0.2-512-int8.mlpackage")
