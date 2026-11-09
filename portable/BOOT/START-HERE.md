# Start P/PPI

1. Read `PIPPI/PIPPI-ADAPTIVE-COLD-BOOT.md` and
   `PIPPI/PIPPI-COMMON-TURN-RECORDS.md`.
2. Read the host adapter instructions under `SKILLS/`.
3. Inspect `BOOT/COLD-BOOT.json` and the THR/DKN/self-certificate records under
   `META/`, then run `python -I -B VERIFY.py PATH-TO-THIS-ARCHIVE.zip`.
   Compare the archive SHA-256 with the value supplied separately by the sender.
   For local execution, extract `UCM/UCM-v0.1-runtime.zip` into a separate empty
   directory and use its CLI and skill instructions.
4. Local hosts run `pippi interface-doctor` and negotiate `EXECUTABLE_LOCAL`.
5. Web hosts select `ARTIFACT_MEDIATED_WEB` and return files through `RETURN/`.
6. Run `pippi standards` to inspect the constitutional standards atlas and
   `pippi pipeline-model` to inspect the governed states and transitions.

This package is INFORMATION_ONLY. It grants no authority and contains no private
credentials.
