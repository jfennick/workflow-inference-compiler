steps:
  wictoolgen:
    in:
      yaml:
        source: yaml
      dir:
        source: dir
      homedir:
        source: homedir
    run: ../../cwl_adapters/wictoolgen.cwl
    out: []
cwlVersion: v1.0
class: Workflow
$namespaces:
  edam: https://edamontology.org/
$schemas:
- https://raw.githubusercontent.com/edamontology/edamontology/master/EDAM_dev.owl
inputs:
  yaml:
    type: File
  dir:
    type: Directory
  homedir:
    type: string
outputs: {}
