import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_comprehensive_real_ats import qualified

scores = [q['match_score'] for q in qualified]
print('Total qualified:', len(scores))
print('Scores >= 70%:', len([s for s in scores if s >= 70]))
print('Scores 50-69%:', len([s for s in scores if s >= 50 and s < 70]))
print('Scores 30-49%:', len([s for s in scores if s >= 30 and s < 50]))
print('Scores < 30%:', len([s for s in scores if s < 30]))

print('\nTop 15 highest scoring real jobs:')
sorted_q = sorted(qualified, key=lambda x: x['match_score'], reverse=True)
for q in sorted_q[:15]:
    c = q['company']
    t = q['title']
    s = q['match_score']
    u = q['url']
    sk = q['matched_skills'][:5]
    print(f'[{c}] {t} - Score: {s}% - Skills: {sk}')
    print(f'  URL: {u}')
