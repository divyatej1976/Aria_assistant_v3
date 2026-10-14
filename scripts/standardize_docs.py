import os
import re
import glob

# Gather all markdown files
docs_dir = 'docs'
all_md_files = glob.glob(os.path.join(docs_dir, '**/*.md'), recursive=True)
all_md_files = sorted([f.replace('\\', '/') for f in all_md_files])

print(f"Found {len(all_md_files)} markdown files.")

# Terminology replacements
term_replacements = [
    (re.compile(r'\bLearner State\b', re.IGNORECASE), 'learner_concept_state'),
    (re.compile(r'\blearner_state\b', re.IGNORECASE), 'learner_concept_state'),
    (re.compile(r'\bConcept State\b', re.IGNORECASE), 'learner_concept_state'),
    (re.compile(r'\bMastery State\b', re.IGNORECASE), 'learner_concept_state'),
    (re.compile(r'\bArchitecture Decision\b', re.IGNORECASE), 'ADR'),
    (re.compile(r'\bArchitectural Record\b', re.IGNORECASE), 'ADR'),
    (re.compile(r'\bArchitectural Decision Record\b', re.IGNORECASE), 'ADR'),
]

# Headings standardization for freeze docs
freeze_heading_replacements = [
    (re.compile(r'^#\s+Cross-Phase Consistency\s*$', re.MULTILINE), '# Cross-Phase Consistency Review'),
    (re.compile(r'^#\s+Review Checklist\s*$', re.MULTILINE), '# Phase Review Checklist'),
    (re.compile(r'^#\s+Freeze Decision\s*$', re.MULTILINE), '# Architecture Freeze'),
]

# We will collect the titles of all files so we can fix "Next" links
file_titles = {}
for file in all_md_files:
    filename = os.path.basename(file)
    if re.match(r'^\d\d-', filename):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'^## Step \d+ — (.*)$', content, re.MULTILINE)
            if match:
                file_titles[file] = match.group(1).strip()
            else:
                match = re.search(r'^# .* — Phase \d+: .*$', content, re.MULTILINE)
                # Fallback to filename
                file_titles[file] = filename[3:].replace('.md', '').replace('-', ' ').title()

# Phase titles
phase_titles = {
    0: 'Vision',
    1: 'Product Requirements',
    2: 'UX',
    3: 'System Architecture',
    4: 'AI Architecture',
    5: 'Memory Architecture',
    6: 'Database Architecture',
    7: 'API Architecture',
    8: 'Agent Architecture',
    9: 'Prompt Engineering'
}

for file in all_md_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. Terminology replacements
    for pattern, replacement in term_replacements:
        # Avoid replacing inside learner_concept_state itself
        content = pattern.sub(replacement, content)
    
    # Ensure "learner_concept_state" isn't duplicated (e.g. learner_concept_state_concept_state)
    # This is a crude fix, but we can just be careful.
    
    # 2. Heading replacements
    filename = os.path.basename(file)
    if 'freeze' in filename:
        for pattern, replacement in freeze_heading_replacements:
            content = pattern.sub(replacement, content)
            
    # Normalize Purpose heading
    content = re.sub(r'^#\s+Purpose\s*$', '## Purpose', content, flags=re.MULTILINE)
    
    # Normalize Next link
    # Find the current Next link
    next_match = re.search(r'^## Next\s*\n\s*(.*)$', content, re.MULTILINE)
    
    match = re.match(r'^(\d\d)-', filename)
    if match:
        step_num = int(match.group(1))
        
        # Determine the phase
        phase_match = re.search(r'phase-(\d+)', file)
        if phase_match:
            phase_num = int(phase_match.group(1))
            
            if step_num < 10:
                # Next is step_num + 1 in the same directory
                next_step = step_num + 1
                next_file_prefix = f"{next_step:02d}-"
                
                # Find the next file in the same directory
                dir_name = os.path.dirname(file)
                next_file = next((f for f in all_md_files if f.startswith(dir_name) and os.path.basename(f).startswith(next_file_prefix)), None)
                
                if next_file and next_file in file_titles:
                    next_text = f"Step {next_step} — {file_titles[next_file]}."
                else:
                    next_text = f"Step {next_step}."
            else:
                # Next is next phase
                next_phase = phase_num + 1
                if next_phase in phase_titles:
                    next_text = f"Phase {next_phase} — {phase_titles[next_phase]}."
                else:
                    next_text = f"Implementation."
            
            if next_match:
                content = content[:next_match.start(1)] + next_text + "\n"
            else:
                content += f"\n---\n\n## Next\n\n{next_text}\n"

    if content != original_content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file}")

print("Done")
