# Copyright 2022 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Tuple, Union

import coremltools as ct
import numpy as np

from transformers.utils import TensorType, is_torch_available, logging
from transformers.modeling_utils import PreTrainedModel

from .config import CoreMLConfig

logger = logging.get_logger(__name__)  # pylint: disable=invalid-name


def validate_model_outputs(
    config: CoreMLConfig,
    preprocessor: Union["PreTrainedTokenizer", "FeatureExtractionMixin", "ProcessorMixin"],
    reference_model: Union["PreTrainedModel", "TFPreTrainedModel"],
    mlmodel: ct.models.MLModel,
    atol: float,
):
    """
    Validate that the outputs from the base and exported model agree within some absolute tolerance.

    Args:
        config ([`~coreml.config.CoreMLConfig`]):
            The Core ML configuration associated with the exported model.
        preprocessor ([`PreTrainedTokenizer`], [`FeatureExtractionMixin`] or [`ProcessorMixin`]):
            The preprocessor used for encoding the data.
        reference_model ([`PreTrainedModel`] or [`TFPreTrainedModel`]):
            The model to export.
        mlmodel (`ct.models.MLModel`):
            The exported Core ML model.
        atol (`float`):
            Absolute tolerance. Differences larger than this value are considered problematic.
    """
    logger.info("Validating Core ML model...")

    input_descs = config.inputs
    output_descs = config.outputs

    if is_torch_available() and issubclass(type(reference_model), PreTrainedModel):
        framework = TensorType.PYTORCH
    else:
        framework = TensorType.TENSORFLOW

    dummy_inputs = config.generate_dummy_inputs_for_validation(preprocessor, framework)

    reference_model_inputs = {}
    coreml_inputs = {}
    for name, (ref_value, coreml_value) in dummy_inputs.items():
        reference_model_inputs[name] = ref_value
        coreml_inputs[input_descs[name].name] = coreml_value

    # Compute outputs from the reference model
    if is_torch_available() and issubclass(type(reference_model), PreTrainedModel):
        reference_model.to("cpu").eval()
    ref_outputs_dict = reference_model(**reference_model_inputs, return_dict=True)

    # Compute outputs from the Core ML model
    coreml_outputs = mlmodel.predict(coreml_inputs)

    # Map the Core ML output names back to the names used by the reference model
    coreml_output_names = list(coreml_outputs.keys())
    coreml_output_internal_names = []
    for name, desc in output_descs.items():
        if desc.name in coreml_output_names:
            coreml_output_internal_names.append(name)

    # Check that keys in coreml_output_internal are a subset of keys from ref_outputs
    ref_outputs_set = set(ref_outputs_dict.keys())
    coreml_outputs_set = set(coreml_output_internal_names)
    if not coreml_outputs_set.issubset(ref_outputs_set):
        logger.info(
            f"\t-[x] Core ML model output names {coreml_outputs_set} do not match reference model {ref_outputs_set}"
        )
        raise ValueError(
            "Outputs doesn't match between reference model and ONNX exported model: "
            f"{coreml_outputs_set.difference(ref_outputs_set)}"
        )
    else:
        logger.info(f"\t-[✓] Core ML model output names match reference model ({coreml_outputs_set})")

    # Check the shape and values match
    for name in coreml_output_internal_names:
        coreml_name = output_descs[name].name
        coreml_value = coreml_outputs[coreml_name]

        if is_torch_available() and issubclass(type(reference_model), PreTrainedModel):
            ref_value = ref_outputs_dict[name].detach().numpy()
        else:
            ref_value = ref_outputs_dict[name].numpy()
        logger.info(f'\t- Validating Core ML model output "{name}":')

        # Shape
        if not coreml_value.shape == ref_value.shape:
            logger.info(f"\t\t-[x] shape {coreml_value.shape} doesn't match {ref_value.shape}")
            raise ValueError(
                "Outputs shape doesn't match between reference model and Core ML exported model: "
                f"Got {ref_value.shape} (reference) and {coreml_value.shape} (Core ML)"
            )
        else:
            logger.info(f"\t\t-[✓] {coreml_value.shape} matches {ref_value.shape}")

        # Values
        if not np.allclose(ref_value, coreml_value, atol=atol):
            logger.info(f"\t\t-[x] values not close enough (atol: {atol})")
            raise ValueError(
                "Outputs values doesn't match between reference model and Core ML exported model: "
                f"Got max absolute difference of: {np.amax(np.abs(ref_value - coreml_value))}"
            )
        else:
            logger.info(f"\t\t-[✓] all values close (atol: {atol})")