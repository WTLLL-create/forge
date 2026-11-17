# Submission templates

`cumcm_template.json` is the machine-readable layout contract.

`CUMCM_template.docx` is a contract-derived bootstrap reference template. It is
not claimed to be an official competition template. The production renderer
must load a reference DOCX and record its SHA-256; creating a blank `Document()`
is forbidden. When an official CUMCM or other competition template is supplied,
replace the reference DOCX and update the JSON metadata. The workflow and gate
do not need to be rewritten.

Rebuild the bootstrap reference with:

```powershell
python build_cumcm_reference_template.py --contract cumcm_template.json --output CUMCM_template.docx
```
