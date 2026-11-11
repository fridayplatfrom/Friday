# Model bundles

No legacy checkpoint is activated by default. Train a complete reviewed-data bundle as described in ../../../docs/TRAINING.md.

- Text pathology: `pathology/{manifest.json,model.pt,vocab.json,metrics.json,splits.json}`.
- Optional neural router: `router/` with the same bundle schema.
- Leaf images: `leaf_vision_mobilenet.pt` and `leaf_vision_manifest.json`.
- Other text tasks: their own bundle directory, registered with `register_neural_expert`.

Runtime loading checks schema, task identity, dimensions, labels, finite parameters and artifact hashes. A reviewed-data marker records an annotation workflow; it does not establish diagnostic quality. Demo bundles are experimental and disabled by default. Models and private training data are gitignored.
