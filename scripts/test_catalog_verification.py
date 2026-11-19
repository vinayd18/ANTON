from anton.ml.registry import (
    ModelRegistry,
    ModelEntityType,
    CheckpointLoadVerification,
    InferenceVerification,
)

reg = ModelRegistry.build_default_catalog()
print("Total models in default catalog:", reg.count())
for m in reg.list_models():
    print(
        f"{m.model_id}: type={m.entity_type.value}, ckpt_avail={m.checkpoint_availability}, "
        f"load={m.checkpoint_load_verification.value}, infer={m.inference_verification.value}, "
        f"prod_ready={m.production_readiness}"
    )

pretrained = reg.filter_by_entity_type(ModelEntityType.PRETRAINED_MODEL)
datasets = reg.filter_by_entity_type(ModelEntityType.DATASET)
training_impls = reg.filter_by_entity_type(ModelEntityType.TRAINING_IMPLEMENTATION)
print(f"Summary: {len(pretrained)} PRETRAINED_MODEL, {len(datasets)} DATASET, {len(training_impls)} TRAINING_IMPLEMENTATION")
