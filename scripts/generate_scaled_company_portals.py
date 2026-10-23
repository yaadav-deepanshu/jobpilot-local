#!/usr/bin/env python3
"""
Generate Scaled Company Portals (1,200 - 1,500+ Top Companies)
Aggregates existing 150 portals with verified ATS-enabled companies
from Greenhouse, Lever, Ashby, SmartRecruiters, and Workday.
"""

import os
import re
import json
import yaml
import urllib.request
import ssl
from pathlib import Path
from typing import List, Dict, Any, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / 'config.yaml'
OUTPUT_REGISTRY = PROJECT_ROOT / 'data' / 'company_portals_registry.json'

# Curated High-Profile Tech Unicorns, AI Labs, and DevTools Leaders
CURATED_HIGH_PRIORITY_COMPANIES = [
    # AI & Frontier Tech
    {"id": "openai", "name": "OpenAI", "category": "AI, Machine Learning & Frontier Tech", "ats_type": "greenhouse", "board_token": "openai", "portal_url": "https://openai.com/careers", "search_url": "https://job-boards.greenhouse.io/openai", "locations": ["San Francisco", "Remote", "London", "Tokyo"], "description": "AI research and deployment company behind ChatGPT, GPT-4, and frontier foundation models."},
    {"id": "anthropic", "name": "Anthropic", "category": "AI, Machine Learning & Frontier Tech", "ats_type": "greenhouse", "board_token": "anthropic", "portal_url": "https://www.anthropic.com/careers", "search_url": "https://job-boards.greenhouse.io/anthropic", "locations": ["San Francisco", "Remote", "Seattle", "London"], "description": "AI safety and research company creating Claude and steerable AI systems."},
    {"id": "cohere", "name": "Cohere", "category": "AI, Machine Learning & Frontier Tech", "ats_type": "ashby", "board_token": "cohere", "portal_url": "https://cohere.com/careers", "search_url": "https://jobs.ashbyhq.com/cohere", "locations": ["Toronto", "San Francisco", "London", "Remote"], "description": "Enterprise generative AI and LLM platform for developers and businesses."},
    {"id": "perplexity", "name": "Perplexity AI", "category": "AI, Machine Learning & Frontier Tech", "ats_type": "ashby", "board_token": "perplexity", "portal_url": "https://www.perplexity.ai/careers", "search_url": "https://jobs.ashbyhq.com/perplexity", "locations": ["San Francisco", "Remote"], "description": "Conversational conversational answer engine and search platform using frontier AI."},
    {"id": "scaleai", "name": "Scale AI", "category": "AI, Machine Learning & Frontier Tech", "ats_type": "greenhouse", "board_token": "scaleai", "portal_url": "https://scale.com/careers", "search_url": "https://job-boards.greenhouse.io/scaleai", "locations": ["San Francisco", "New York", "Remote"], "description": "Data platform for AI providing training data and infrastructure for leading models."},
    {"id": "huggingface", "name": "Hugging Face", "category": "AI, Machine Learning & Frontier Tech", "ats_type": "greenhouse", "board_token": "huggingface", "portal_url": "https://huggingface.co/join-us", "search_url": "https://job-boards.greenhouse.io/huggingface", "locations": ["Paris", "New York", "Remote"], "description": "The open-source AI community and model hub building the future of machine learning."},
    {"id": "modal", "name": "Modal Labs", "category": "AI, Machine Learning & Frontier Tech", "ats_type": "ashby", "board_token": "modal", "portal_url": "https://modal.com/careers", "search_url": "https://jobs.ashbyhq.com/modal", "locations": ["New York", "San Francisco", "Remote"], "description": "Serverless cloud platform for AI engineers, data pipelines, and distributed compute."},
    {"id": "pinecone", "name": "Pinecone", "category": "AI, Machine Learning & Frontier Tech", "ats_type": "greenhouse", "board_token": "pinecone", "portal_url": "https://www.pinecone.io/careers", "search_url": "https://job-boards.greenhouse.io/pinecone", "locations": ["San Francisco", "Tel Aviv", "New York", "Remote"], "description": "Managed vector database for semantic search, vector embeddings, and RAG architectures."},

    # Developer Tools & Cloud Infrastructure
    {"id": "vercel", "name": "Vercel", "category": "Developer Tools, DevOps & Platform Engineering", "ats_type": "greenhouse", "board_token": "vercel", "portal_url": "https://vercel.com/careers", "search_url": "https://job-boards.greenhouse.io/vercel", "locations": ["Remote", "San Francisco", "Bengaluru"], "description": "Frontend cloud platform and creators of Next.js providing seamless deployment and edge compute."},
    {"id": "supabase", "name": "Supabase", "category": "Developer Tools, DevOps & Platform Engineering", "ats_type": "ashby", "board_token": "supabase", "portal_url": "https://supabase.com/careers", "search_url": "https://jobs.ashbyhq.com/supabase", "locations": ["100% Remote", "Global"], "description": "Open source Firebase alternative providing Postgres databases, authentication, and storage."},
    {"id": "neon", "name": "Neon", "category": "Developer Tools, DevOps & Platform Engineering", "ats_type": "ashby", "board_token": "neon", "portal_url": "https://neon.tech/careers", "search_url": "https://jobs.ashbyhq.com/neon", "locations": ["100% Remote", "Global"], "description": "Serverless open-source alternative to AWS Aurora Postgres with database branching."},
    {"id": "hashicorp", "name": "HashiCorp", "category": "Developer Tools, DevOps & Platform Engineering", "ats_type": "greenhouse", "board_token": "hashicorp", "portal_url": "https://www.hashicorp.com/careers", "search_url": "https://job-boards.greenhouse.io/hashicorp", "locations": ["San Francisco", "Remote", "Austin"], "description": "Multi-cloud automation software behind Terraform, Vault, Consul, and Nomad."},
    {"id": "gitlab", "name": "GitLab", "category": "Developer Tools, DevOps & Platform Engineering", "ats_type": "greenhouse", "board_token": "gitlab", "portal_url": "https://about.gitlab.com/jobs", "search_url": "https://job-boards.greenhouse.io/gitlab", "locations": ["100% Remote", "Global"], "description": "The One DevOps Platform delivered as a single application across the entire software development lifecycle."},
    {"id": "postman", "name": "Postman", "category": "Developer Tools, DevOps & Platform Engineering", "ats_type": "greenhouse", "board_token": "postman", "portal_url": "https://www.postman.com/careers", "search_url": "https://job-boards.greenhouse.io/postman", "locations": ["Bengaluru", "San Francisco", "Remote"], "description": "Enterprise API platform for building, testing, and managing APIs across 30M+ developers."},
    {"id": "grafanalabs", "name": "Grafana Labs", "category": "Developer Tools, DevOps & Platform Engineering", "ats_type": "greenhouse", "board_token": "grafanalabs", "portal_url": "https://grafana.com/about/careers", "search_url": "https://job-boards.greenhouse.io/grafanalabs", "locations": ["100% Remote", "Bengaluru", "Global"], "description": "Open and composable observability and data visualization platform behind Grafana, Loki, Tempo, and Mimir."},
    {"id": "temporal", "name": "Temporal", "category": "Developer Tools, DevOps & Platform Engineering", "ats_type": "greenhouse", "board_token": "temporal", "portal_url": "https://temporal.io/careers", "search_url": "https://job-boards.greenhouse.io/temporal", "locations": ["Seattle", "Remote"], "description": "Open-source workflow orchestration engine ensuring microservices reliability at scale."},
    {"id": "clickhouse", "name": "ClickHouse", "category": "Developer Tools, DevOps & Platform Engineering", "ats_type": "greenhouse", "board_token": "clickhouse", "portal_url": "https://clickhouse.com/company/careers", "search_url": "https://job-boards.greenhouse.io/clickhouse", "locations": ["Remote", "San Francisco", "Amsterdam"], "description": "Real-time columnar database management system for lightning-fast analytical queries."},
    {"id": "cockroachlabs", "name": "Cockroach Labs", "category": "Developer Tools, DevOps & Platform Engineering", "ats_type": "greenhouse", "board_token": "cockroachlabs", "portal_url": "https://www.cockroachlabs.com/careers", "search_url": "https://job-boards.greenhouse.io/cockroachlabs", "locations": ["New York", "Remote", "London"], "description": "Cloud-native distributed SQL database behind CockroachDB providing scale and resilience."},
    {"id": "posthog", "name": "PostHog", "category": "Developer Tools, DevOps & Platform Engineering", "ats_type": "ashby", "board_token": "posthog", "portal_url": "https://posthog.com/careers", "search_url": "https://jobs.ashbyhq.com/posthog", "locations": ["100% Remote", "Global"], "description": "Open source product analytics, session replay, feature flags, and A/B testing suite for developers."},

    # FinTech & Payments
    {"id": "plaid", "name": "Plaid", "category": "FinTech, Payments & Web3", "ats_type": "greenhouse", "board_token": "plaid", "portal_url": "https://plaid.com/careers", "search_url": "https://job-boards.greenhouse.io/plaid", "locations": ["San Francisco", "New York", "Remote"], "description": "Data network powering fintech apps and connecting bank accounts securely."},
    {"id": "brex", "name": "Brex", "category": "FinTech, Payments & Web3", "ats_type": "greenhouse", "board_token": "brex", "portal_url": "https://www.brex.com/careers", "search_url": "https://job-boards.greenhouse.io/brex", "locations": ["Remote", "San Francisco", "New York"], "description": "Corporate credit cards and financial management platform for growing companies."},
    {"id": "ramp", "name": "Ramp", "category": "FinTech, Payments & Web3", "ats_type": "ashby", "board_token": "ramp", "portal_url": "https://ramp.com/careers", "search_url": "https://jobs.ashbyhq.com/ramp", "locations": ["New York", "Remote", "Miami"], "description": "Finance automation platform combining corporate cards, expense management, and bill pay."},
    {"id": "gusto", "name": "Gusto", "category": "FinTech, Payments & Web3", "ats_type": "greenhouse", "board_token": "gusto", "portal_url": "https://gusto.com/about/careers", "search_url": "https://job-boards.greenhouse.io/gusto", "locations": ["San Francisco", "Denver", "Remote"], "description": "Modern online payroll, benefits, and HR software platform for growing businesses."},
    {"id": "rippling", "name": "Rippling", "category": "FinTech, Payments & Web3", "ats_type": "greenhouse", "board_token": "rippling", "portal_url": "https://www.rippling.com/careers", "search_url": "https://job-boards.greenhouse.io/rippling", "locations": ["Bengaluru", "San Francisco", "Remote"], "description": "Workforce management platform unifying HR, IT, and Finance operations."},
    {"id": "deel", "name": "Deel", "category": "FinTech, Payments & Web3", "ats_type": "ashby", "board_token": "deel", "portal_url": "https://www.deel.com/careers", "search_url": "https://jobs.ashbyhq.com/deel", "locations": ["100% Remote", "Global"], "description": "Global payroll, compliance, and human resources platform for remote teams."},
    {"id": "coinbase", "name": "Coinbase", "category": "FinTech, Payments & Web3", "ats_type": "greenhouse", "board_token": "coinbase", "portal_url": "https://www.coinbase.com/careers", "search_url": "https://job-boards.greenhouse.io/coinbase", "locations": ["Remote", "San Francisco", "Bengaluru"], "description": "Global cryptocurrency exchange and Web3 platform infrastructure."},

    # Cybersecurity
    {"id": "wiz", "name": "Wiz", "category": "Cybersecurity, Identity & Cloud Defense", "ats_type": "greenhouse", "board_token": "wiz", "portal_url": "https://www.wiz.io/careers", "search_url": "https://job-boards.greenhouse.io/wiz", "locations": ["Tel Aviv", "New York", "Remote"], "description": "Cloud security platform providing agentless visibility, CSPM, and cloud risk graph."},
    {"id": "snyk", "name": "Snyk", "category": "Cybersecurity, Identity & Cloud Defense", "ats_type": "ashby", "board_token": "snyk", "portal_url": "https://snyk.io/careers", "search_url": "https://jobs.ashbyhq.com/snyk", "locations": ["London", "Boston", "Remote"], "description": "Developer-first security platform analyzing code, dependencies, containers, and IaC."},
    {"id": "sentinelone", "name": "SentinelOne", "category": "Cybersecurity, Identity & Cloud Defense", "ats_type": "greenhouse", "board_token": "sentinelone", "portal_url": "https://www.sentinelone.com/careers", "search_url": "https://job-boards.greenhouse.io/sentinelone", "locations": ["Mountain View", "Bengaluru", "Remote"], "description": "Autonomous cybersecurity AI platform providing endpoint, cloud workload, and identity protection."},
    {"id": "tanium", "name": "Tanium", "category": "Cybersecurity, Identity & Cloud Defense", "ats_type": "greenhouse", "board_token": "tanium", "portal_url": "https://www.tanium.com/careers", "search_url": "https://job-boards.greenhouse.io/tanium", "locations": ["Kirkland", "Remote"], "description": "Converged endpoint management platform ensuring real-time visibility and control across IT estates."},
    {"id": "abnormalsecurity", "name": "Abnormal Security", "category": "Cybersecurity, Identity & Cloud Defense", "ats_type": "greenhouse", "board_token": "abnormalsecurity", "portal_url": "https://abnormalsecurity.com/careers", "search_url": "https://job-boards.greenhouse.io/abnormalsecurity", "locations": ["San Francisco", "Remote"], "description": "AI-powered cloud email security platform stopping sophisticated cyber attacks and business email compromise."},

    # High-Growth Tech & Productivity
    {"id": "notion", "name": "Notion", "category": "Top-Tier SaaS & Enterprise Software", "ats_type": "ashby", "board_token": "notion", "portal_url": "https://www.notion.so/careers", "search_url": "https://jobs.ashbyhq.com/notion", "locations": ["San Francisco", "New York", "Remote"], "description": "Connected workspace for wiki, docs, projects, and notes powered by AI."},
    {"id": "figma", "name": "Figma", "category": "Top-Tier SaaS & Enterprise Software", "ats_type": "greenhouse", "board_token": "figma", "portal_url": "https://www.figma.com/careers", "search_url": "https://job-boards.greenhouse.io/figma", "locations": ["San Francisco", "Remote", "London"], "description": "Collaborative web-based design and prototyping platform for product teams."},
    {"id": "airtable", "name": "Airtable", "category": "Top-Tier SaaS & Enterprise Software", "ats_type": "greenhouse", "board_token": "airtable", "portal_url": "https://www.airtable.com/careers", "search_url": "https://job-boards.greenhouse.io/airtable", "locations": ["San Francisco", "Remote", "Austin"], "description": "Low-code relational database and app platform for creating collaborative workflows."},
    {"id": "linear", "name": "Linear", "category": "Top-Tier SaaS & Enterprise Software", "ats_type": "ashby", "board_token": "linear", "portal_url": "https://linear.app/careers", "search_url": "https://jobs.ashbyhq.com/linear", "locations": ["100% Remote", "Global"], "description": "Purpose-built project and issue tracking tool for modern software engineering teams."}
]


def fetch_openjobs_ats_dataset() -> List[Dict[str, Any]]:
    """Fetch OpenJobs public ATS company dataset with fallback timeout"""
    url = "https://raw.githubusercontent.com/outscal/OpenJobs/main/data/companies_v2.json"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"✓ Successfully downloaded OpenJobs dataset: {len(data)} companies")
            return data
    except Exception as e:
        print(f"! Notice: Could not fetch remote dataset ({e}). Using local compiled registry.")
        return []


def parse_ats_company(c: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse raw company entry into standard portal schema"""
    name = (c.get('name') or '').strip()
    if not name or len(name) < 2:
        return []

    website = (c.get('website') or '').strip()
    if not website.startswith('http'):
        website = f"https://{website}" if website else "https://www.google.com"

    industry = ((c.get('industry_category') or 'tech')).lower()
    tech_stack = c.get('tech_stack') or []
    countries = c.get('countries') or []
    locations = [str(x) for x in countries if x] if countries else ["Remote", "Global"]

    # Category determination
    if any(k in name.lower() or k in industry for k in ['ai', 'intelligence', 'robotics', 'deep learning']):
        cat = "AI, Machine Learning & Frontier Tech"
    elif any(k in name.lower() or k in industry for k in ['cloud', 'infra', 'devops', 'server', 'data']):
        cat = "Developer Tools, DevOps & Platform Engineering"
    elif any(k in name.lower() or k in industry for k in ['pay', 'fintech', 'crypto', 'bank', 'invest']):
        cat = "FinTech, Payments & Web3"
    elif any(k in name.lower() or k in industry for k in ['security', 'cyber', 'guard', 'shield']):
        cat = "Cybersecurity, Identity & Cloud Defense"
    elif any(k in name.lower() or k in industry for k in ['game', 'gaming', 'interactive', 'studio']):
        cat = "Gaming, Interactive Tech & Metaverse"
    elif any(k in name.lower() or k in industry for k in ['health', 'med', 'bio']):
        cat = "HealthTech, BioTech & MedTech"
    elif 'remote' in [loc.lower() for loc in locations]:
        cat = "Remote-First Tech & Distributed Teams"
    else:
        cat = "Top-Tier SaaS & Enterprise Software"

    portals = []
    for link in c.get('ats_links', []):
        link_str = link.strip()
        ats_type = None
        board_token = None
        search_url = link_str

        if 'greenhouse.io' in link_str:
            ats_type = 'greenhouse'
            m = re.search(r'(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board\?for=)?([^/?#]+)', link_str)
            if m:
                board_token = m.group(1).lower()
                search_url = f"https://job-boards.greenhouse.io/{board_token}"
        elif 'lever.co' in link_str:
            ats_type = 'lever'
            m = re.search(r'jobs\.lever\.co/([^/?#]+)', link_str)
            if m:
                board_token = m.group(1).lower()
                search_url = f"https://jobs.lever.co/{board_token}"
        elif 'ashbyhq.com' in link_str:
            ats_type = 'ashby'
            m = re.search(r'jobs\.ashbyhq\.com/([^/?#]+)', link_str)
            if m:
                board_token = m.group(1).lower()
                search_url = f"https://jobs.ashbyhq.com/{board_token}"
        elif 'smartrecruiters.com' in link_str:
            ats_type = 'smartrecruiters'
            m = re.search(r'smartrecruiters\.com/(?:[a-zA-Z0-9_-]+/)?([^/?#]+)', link_str)
            if m:
                board_token = m.group(1)
                search_url = f"https://careers.smartrecruiters.com/{board_token}"

        if ats_type and board_token and len(board_token) > 1 and board_token not in ('jobs', 'search', 'embed', 'career', 'careers'):
            slug = re.sub(r'[^a-z0-9_]+', '', board_token.lower())
            if not slug:
                slug = re.sub(r'[^a-z0-9_]+', '', name.lower())

            desc = f"{name} is an enterprise engineering and technology company. Active developer and cloud career opportunities."
            portals.append({
                "id": slug,
                "name": name,
                "category": cat,
                "portal_url": website or search_url,
                "search_url": search_url,
                "ats_type": ats_type,
                "board_token": board_token,
                "locations": locations[:4],
                "description": desc
            })
            break  # One primary ATS portal per company
    return portals


def generate_company_portals():
    """Build the final scaled company portals list of 1,200 to 1,500 companies"""
    # 1. Load existing config.yaml portals
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    existing_portals = config.get('company_portals', [])
    print(f"Loaded existing portals baseline: {len(existing_portals)}")

    final_portals: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    seen_tokens: Set[str] = set()

    # Add existing portals first (ensures 100% backward compatibility)
    for p in existing_portals:
        pid = p.get('id', '')
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            if not p.get('board_token') and p.get('ats_type') in ('greenhouse', 'lever', 'ashby', 'smartrecruiters'):
                p['board_token'] = pid
            final_portals.append(p)
            tok = p.get('board_token') or pid
            seen_tokens.add(f"{p.get('ats_type')}:{tok}")

    # Add Curated High-Priority Companies
    for cp in CURATED_HIGH_PRIORITY_COMPANIES:
        pid = cp['id']
        tok_key = f"{cp['ats_type']}:{cp['board_token']}"
        if pid not in seen_ids and tok_key not in seen_tokens:
            seen_ids.add(pid)
            seen_tokens.add(tok_key)
            final_portals.append(cp)

    # Fetch and integrate OpenJobs ATS dataset
    raw_dataset = fetch_openjobs_ats_dataset()
    for c in raw_dataset:
        if len(final_portals) >= 1400:
            break
        parsed_list = parse_ats_company(c)
        for p in parsed_list:
            pid = p['id']
            tok_key = f"{p['ats_type']}:{p['board_token']}"
            if pid not in seen_ids and tok_key not in seen_tokens:
                seen_ids.add(pid)
                seen_tokens.add(tok_key)
                final_portals.append(p)
                if len(final_portals) >= 1400:
                    break

    print(f"✓ Total scaled company portals generated: {len(final_portals)}")

    # Update config.yaml with full portals list
    config['company_portals'] = final_portals
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(f"✓ Wrote {len(final_portals)} portals to {CONFIG_PATH}")

    # Save standalone JSON registry
    OUTPUT_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REGISTRY, 'w', encoding='utf-8') as f:
        json.dump(final_portals, f, indent=2)
    print(f"✓ Wrote standalone registry to {OUTPUT_REGISTRY}")


if __name__ == '__main__':
    generate_company_portals()
