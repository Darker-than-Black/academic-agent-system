"""Reproduce one isolated validator defect; pass the audited checkout directory."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
expected_sha = 'be4ba4755bf1b52220f25e13b2293b5956590070'
actual_sha = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
assert actual_sha == expected_sha, (actual_sha, expected_sha)
source = root / 'researchclaw/hitl/claim_verifier.py'
spec = importlib.util.spec_from_file_location('audited_verifier', source)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
    project = Path(directory)
    (project / 'stage-14').mkdir()
    summary = {'training_seconds': 95, 'test_accuracy': 0.51}
    (project / 'stage-14/experiment_summary.json').write_text(json.dumps(summary))
    claim = module.Claim(text='Our model achieves 95% test accuracy.', claim_type='numerical')
    module.ClaimVerifier(project)._verify_numerical(claim)
    print(json.dumps({'summary': summary, 'verdict': claim.to_dict()}, indent=2))
    assert claim.grounded is True, 'Audited false positive did not reproduce'
