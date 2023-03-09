steps:
  wictoolgen:
    in:
      yaml:
        source: yaml
      homedir:
        source: homedir
    run: ../../cwl_adapters/wictoolgen.cwl
    out: []
cwlVersion: v1.2
class: Workflow
$namespaces:
  edam: https://edamontology.org/
$schemas:
- https://raw.githubusercontent.com/edamontology/edamontology/master/EDAM_dev.owl
inputs:
  yaml:
    type: File
  homedir:
    type: string
outputs: {}
