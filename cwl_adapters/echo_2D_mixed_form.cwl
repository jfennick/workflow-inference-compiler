baseCommand: echo
class: CommandLineTool
cwlVersion: v1.0
inputs:
  message:
    inputBinding:
      position: 1
    type:
      items: string[]
      type: array
outputs:
  stdout:
    outputBinding:
      glob: stdout
    type: File
stdout: stdout
