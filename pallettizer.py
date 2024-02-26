import coremltools as ct
import coremltools.optimize.coreml as cto


uncompressed_model_path = "./mistral-7b-instruct-v0.2-512-fp16.mlpackage"
mlmodel = ct.models.MLModel(uncompressed_model_path)
op_config = cto.OpPalettizerConfig(mode="kmeans", nbits=4)
config = cto.OptimizationConfig(global_config=op_config)
compressed_mlmodel = cto.palettize_weights(mlmodel, config)
compressed_mlmodel.save("mistral-7b-instruct-v0.2-512-int4.mlpackage")
