def generate_deduplication_prompt(keywords_list, brand_name=None):
    """Generate prompt for keyword deduplication"""
    
    brand_clause = f"\n4. REMOVE brand names (except {brand_name})" if brand_name else "\n4. REMOVE brand names"
    
    prompt = f"""You are a keyword cleaning specialist.

TASK: Remove duplicates and low-value variations from this keyword list.

RULES:

1. WORD-ORDER DUPLICATES → KEEP ONE
   - "cheap glasses online" = "glasses online cheap" → Keep the more natural one
   - "affordable prescription glasses" = "prescription affordable glasses" → Keep one
   
2. SEMANTIC VARIATIONS → KEEP BOTH
   - "cheap" vs "affordable" → KEEP BOTH (different words, same intent is OK)
   - "eyeglasses" vs "spectacles" → KEEP BOTH
   
3. NORMALIZE PLURALS
   - If both "glass" and "glasses" exist → Keep "glasses" (more common)
{brand_clause}
   - Flag potential brand names as brands to remove
   - Examples: "warby parker", "zenni optical", "rx glasses" (might be brand RxGlasses)

5. NONSENSICAL VARIATIONS
   - Remove awkward word orders that no one would actually search

INPUT KEYWORDS ({len(keywords_list)} total):
{', '.join(keywords_list)}

OUTPUT FORMAT (JSON ONLY):
{{
  "kept_keywords": [
    "keyword 1",
    "keyword 2",
    ...
  ],
  "removed": {{
    "duplicates": [
      "glasses online cheap (duplicate of 'cheap glasses online')",
      ...
    ],
    "brands": [
      "warby parker",
      "rx glasses",
      ...
    ]
  }},
  "dedup_summary": "Removed X duplicates, Y brands. Kept W keywords."
}}

RETURN ONLY VALID JSON. NO MARKDOWN, NO EXPLANATION."""
    
    return prompt


def generate_traffic_clustering_prompt(topic, keywords_list, brand_name=""):
    """Generate clustering prompt for traffic blogs"""
    
    brand_clause = f"besides {brand_name}" if brand_name else ""
    
    prompt = f"""You are an SEO strategist for QYUBIC, a discount savings startup in UAE.

TRAFFIC BLOG: Broad commercial intent, comparisons, 'Best X' lists

TOPIC: {topic}

# CRITICAL TASKS:

## 1. CLUSTER BY USER PSYCHOLOGY
Group by: "What problem/anxiety is the user solving?"
Create 6-10 sub-intent clusters.

## 2. KEYWORD-LEVEL PRIORITY (CRITICAL!)
Assign priority to EACH keyword individually:

**HIGH**: Core intent, strong volume, clear need
**MEDIUM**: Supporting term, moderate value
**LOW**: Weak variation, potential brand, unclear intent, very low/no volume

Example:
- "cheap glasses online" → HIGH (strong intent)
- "affordable prescription glasses" → HIGH (strong intent)
- "discount eyeglasses online" → MEDIUM (synonym)
- "cheapest varifocal glasses" → LOW (too specific)
- "rx glasses" → LOW (possible brand)

## 3. ADD AI-SUGGESTED COVERAGE (ADD 3-5 PER MAJOR CLUSTER!)
Fill semantic gaps - concepts readers expect to see:

Eyeglasses: "PD measurement", "virtual try-on", "return policy", "lens types", "anti-reflective coating"
Skincare: "hyaluronic acid", "niacinamide", "UAE climate factors", "morning/night routine"
Electronics: "processor specs", "battery life", "warranty coverage", "gaming performance"

RULES:
- Add 3-5 per major cluster (not just 1!)
- Must be logically necessary
- Tag as "source": "AI Suggested"
- Set priority: HIGH if crucial, MEDIUM if supporting

## 4. OUTPUT JSON:
{{
  "clusters": [
    {{
      "cluster_name": "Online Ordering Anxiety",
      "role": "Core Pain Point",
      "placement": "H2",
      "keywords": [
        {{"keyword": "can i trust online eyewear", "source": "GKP", "priority": "HIGH"}},
        {{"keyword": "virtual try-on accuracy", "source": "AI Suggested", "priority": "HIGH"}},
        {{"keyword": "return policy glasses", "source": "AI Suggested", "priority": "HIGH"}},
        {{"keyword": "customer reviews", "source": "AI Suggested", "priority": "MEDIUM"}},
        {{"keyword": "fraud protection", "source": "AI Suggested", "priority": "MEDIUM"}}
      ],
      "coverage_notes": "Main user anxiety"
    }}
  ],
  "missing_faq_opportunities": [
    "What if glasses don't fit?",
    "Can I return prescription glasses?",
    "How accurate is virtual try-on?",
    "Do online glasses have warranties?",
    "How long for prescription verification?"
  ]
}}

KEYWORDS TO CLUSTER:
{', '.join(keywords_list)}

RETURN ONLY VALID JSON. NO MARKDOWN, NO EXPLANATION."""
    
    return prompt


def generate_archetype_prompt(brand_context):
    """Generate prompt for user archetype identification (positioning blogs)"""
    
    services_text = '\n'.join([f"- {s}" for s in brand_context['services'] if s.strip()])
    
    prompt = f"""You are a customer psychology researcher for {brand_context['brand_name']}.

BRAND CONTEXT:
- Industry: {brand_context['industry']}
- Services:
{services_text}
- Target Market: {brand_context['target_market']}
- Content Goal: {brand_context['content_goal']}

TASK:
Identify 3-5 user archetypes who would benefit from these services.

For EACH archetype, identify:
1. WHO they are (demographic + situation)
2. PAIN POINTS (emotional + logistical stress)
3. EMOTIONAL NEEDS (what would relieve anxiety)
4. STRESSFUL SCENARIOS (when do they need this service)

OUTPUT FORMAT (JSON ONLY):
{{
  "Families with Young Children": {{
    "who": "Parents traveling with toddlers/infants through busy airports",
    "pain_points": [
      "Stroller handling through security checkpoints",
      "Children getting tired and cranky during long waits",
      "Managing luggage while keeping kids safe",
      "Long immigration queues with restless children"
    ],
    "emotional_needs": [
      "Reduced chaos and stress",
      "Faster navigation through airport",
      "Peace of mind about child safety",
      "Less judgment from other travelers"
    ],
    "stressful_scenarios": [
      "Early morning flights with sleepy children",
      "Long layovers with limited child-friendly facilities",
      "First-time international travel with kids",
      "Traveling alone with multiple children"
    ]
  }},
  "Elderly Travelers": {{
    "who": "Senior citizens 65+ traveling independently or with family",
    "pain_points": [
      "Long walking distances between gates",
      "Difficulty standing in long queues",
      "Confusion with airport signage and navigation",
      "Physical exhaustion from carrying luggage"
    ],
    "emotional_needs": [
      "Dignity and independence",
      "Physical comfort and rest",
      "Clear guidance and support",
      "Reduced anxiety about getting lost"
    ],
    "stressful_scenarios": [
      "Tight connection times between flights",
      "Terminal changes requiring shuttle buses",
      "Peak hours with crowded facilities",
      "Medical concerns during travel"
    ]
  }}
}}

RETURN ONLY VALID JSON. NO MARKDOWN, NO EXPLANATION."""
    
    return prompt


def generate_validation_keywords_prompt(brand_context, archetypes, manual_research):
    """Generate SEO validation keywords from archetypes and research"""
    
    import json
    
    prompt = f"""You are an SEO keyword researcher.

BRAND: {brand_context['brand_name']} - {brand_context['industry']}
CONTENT GOAL: {brand_context['content_goal']}

USER ARCHETYPES & PSYCHOLOGY:
{json.dumps(archetypes, indent=2)}

MANUAL RESEARCH FINDINGS:
{json.dumps(manual_research, indent=2)}

TASK:
Generate 15-25 keyword seeds to search in Google Keyword Planner.

These should:
1. Bridge psychology → SEO language
2. Include emotional modifiers from research findings
3. Cover each archetype's pain points
4. Use natural user phrasing from Reddit/forums/AnswerThePublic
5. Include brand name + problem combinations
6. Include comparison terms if relevant

EXAMPLES:
- "airport assistance for elderly"
- "dubai airport fast track families"
- "wheelchair service dubai airport"
- "meet and greet dubai airport senior"
- "airport lounge access with toddlers"
- "dubai airport help disabled passengers"

OUTPUT FORMAT (JSON ONLY):
{{
  "keyword_seeds": [
    "airport assistance for seniors",
    "fast track immigration dubai families",
    "wheelchair assistance dubai airport",
    ...
  ],
  "rationale": "Brief explanation: These keywords combine user archetypes (families, elderly) with their specific pain points (fast track, wheelchair) and include location modifier (dubai) for local SEO."
}}

RETURN ONLY VALID JSON. NO MARKDOWN, NO EXPLANATION."""
    
    return prompt


def generate_positioning_clustering_prompt(brand_context, keywords_list, archetypes):
    """Generate clustering prompt for positioning blogs"""
    
    import json
    
    prompt = f"""You are an SEO content strategist for POSITIONING blogs.

BRAND: {brand_context['brand_name']}
INDUSTRY: {brand_context['industry']}
CONTENT GOAL: {brand_context['content_goal']}

USER ARCHETYPES:
{json.dumps(archetypes, indent=2)}

KEYWORDS TO CLUSTER:
{', '.join(keywords_list)}

TASK:
1. Cluster keywords by PAIN POINT (not just semantic similarity)
2. Map clusters to archetypes where relevant
3. Assign keyword-level priority (HIGH/MEDIUM/LOW)
4. Add AI-suggested coverage (trust signals, objections, comparisons)
5. Identify FAQ opportunities

POSITIONING FOCUS:
- Prioritize trust-building terms
- Highlight comparison opportunities (vs competitors, vs DIY)
- Flag objection-removal keywords
- Identify brand positioning angles

OUTPUT (JSON):
{{
  "clusters": [
    {{
      "cluster_name": "Airport Navigation Stress",
      "linked_archetype": "Families with Young Children",
      "role": "Core Pain Point",
      "positioning_angle": "How {brand_context['brand_name']} removes navigation stress for families",
      "placement": "H2",
      "keywords": [
        {{"keyword": "airport help with stroller", "priority": "HIGH", "source": "GKP"}},
        {{"keyword": "family lounge access dubai", "priority": "HIGH", "source": "GKP"}},
        {{"keyword": "child-friendly airport assistance", "priority": "MEDIUM", "source": "AI Suggested"}},
        {{"keyword": "travel with toddlers airport tips", "priority": "MEDIUM", "source": "AI Suggested"}}
      ],
      "coverage_notes": "Address fear of managing kids through busy airport"
    }}
  ],
  "missing_faq_opportunities": [
    "How early should I book airport assistance?",
    "Is the service suitable for toddlers?",
    "What if my flight is delayed?"
  ],
  "positioning_hooks": [
    "Why {brand_context['brand_name']} is better than navigating alone",
    "{brand_context['brand_name']} vs hiring private airport concierge"
  ]
}}

RETURN ONLY VALID JSON. NO MARKDOWN, NO EXPLANATION."""
    
    return prompt

def generate_conversion_deduplication_prompt(keywords_list, brand_name, product_name, competitor_products):
    """Generate deduplication prompt for conversion blogs - KEEPS brand variations"""
    
    competitor_list = ', '.join(competitor_products) if competitor_products else "none specified"
    
    prompt = f"""You are a keyword cleaning specialist for CONVERSION blogs.

PRODUCT CONTEXT:
- Brand: {brand_name}
- Product: {product_name}
- Competitors: {competitor_list}

CONVERSION BLOG DEDUPLICATION RULES:

1. KEEP ALL BRAND + PRODUCT VARIATIONS
   - keep different spellings of the brand product - short + long form

2. KEEP MEANINGFUL SEMANTIC VARIATIONS
   - "cheap" vs "affordable" vs "budget" → KEEP ALL (different user language)
   - "review" vs "reviews" → KEEP ONE (just plural normalization)

3. REMOVE ONLY EXACT DUPLICATES
   - Exact same keywords appearing twice → Remove duplicate

4. FLAG COMPETITOR BRANDS (don't remove, just flag)
   - Mark competitor products for separate cluster
   - Examples: {competitor_list}

5. NORMALIZE PLURALS ONLY
   - "serum" vs "serums" → Keep "serum" (more natural)

INPUT KEYWORDS ({len(keywords_list)} total):
{', '.join(keywords_list)}

OUTPUT FORMAT (JSON ONLY):
{{
  "kept_keywords": [
    "keyword 1",
    "keyword 2",
    ...
  ],
  "removed": {{
    "exact_duplicates": [
      "duplicate keyword (exact match of ...)",
      ...
    ]
  }},
  "competitor_keywords": [
    "competitor product 1 keyword",
    "competitor product 2 keyword",
    ...
  ],
  "dedup_summary": "Removed X exact duplicates. Kept Y keywords including Z brand variations and W competitor mentions."
}}

RETURN ONLY VALID JSON. NO MARKDOWN, NO EXPLANATION."""
    
    return prompt

def generate_conversion_clustering_prompt(product_context, keywords_list):
    """Generate clustering prompt for conversion blogs - objection-focused"""
    
    competitor_text = ', '.join(product_context.get('competitor_products', []))
    
    prompt = f"""You are an SEO content strategist for CONVERSION blogs.

PRODUCT CONTEXT:
- Brand: {product_context['brand_name']}
- Product: {product_context['product_name']}
- Category: {product_context['product_category']}
- Competitors: {competitor_text}

CONVERSION BLOG FOCUS:
Remove purchase objections, validate product claims, and drive buying decisions.

KEYWORDS TO CLUSTER:
{', '.join(keywords_list)}

TASK:
1. Cluster keywords by OBJECTION TYPE (not just semantic similarity)
2. Assign keyword-level priority (HIGH/MEDIUM/LOW)
3. Add AI-suggested coverage (missing objections, comparison angles)
4. Identify FAQ opportunities (pre-purchase questions)

OBJECTION TYPES (use these as cluster inspiration):
- Price Concerns ("is it worth it", "overpriced", "cheaper alternative")
- Efficacy Doubts ("does it work", "results", "before after")
- Direct Comparisons ("{product_context['product_name']} vs [competitor]")
- Safety/Side Effects ("safe for X", "ingredients concern", "allergic reaction")
- Purchase Logistics ("where to buy", "shipping", "return policy", "authentic")
- Product Specs ("how to use", "how long does it last", "size", "shelf life")
- Social Proof ("reviews", "testimonials", "influencer opinions")

PRIORITY RULES:
- HIGH: Direct objection removal, strong buying intent, comparison keywords
- MEDIUM: Supporting validation, related concerns
- LOW: Weak variations, tangential topics

AI-SUGGESTED COVERAGE (add 2-4 per major objection):
- Missing comparison angles
- Unaddressed concerns from product reviews
- Purchase decision factors

OUTPUT (JSON):
{{
  "clusters": [
    {{
      "cluster_name": "Price Justification",
      "objection_type": "Price Concerns",
      "role": "Remove price objection",
      "placement": "H2",
      "keywords": [
        {{"keyword": "is {product_context['product_name']} worth it", "priority": "HIGH", "source": "GKP"}},
        {{"keyword": "{product_context['product_name']} price", "priority": "HIGH", "source": "GKP"}},
        {{"keyword": "cost per use analysis", "priority": "MEDIUM", "source": "AI Suggested"}},
        {{"keyword": "cheaper alternatives comparison", "priority": "MEDIUM", "source": "AI Suggested"}}
      ],
      "coverage_notes": "Address ROI, cost-per-use, and alternative options"
    }},
    {{
      "cluster_name": "Features",
      "objection_type": "Exploring Product",
      "role": "Clarifying features or benefits",
      "placement": "H2",
      "keywords": [
        {{"keyword": "{product_context['product_name']} vitamin c?", "priority": "HIGH", "source": "GKP"}},
        {{"keyword": "is it good for pigmentation", "priority": "MEDIUM", "source": "AI Suggested"}},
      ],
      "coverage_notes": "Direct feature/benefit table"
    }}
  ],
  "missing_faq_opportunities": [
    "How long until I see results?",
    "Can I use this with retinol?",
    "Is it suitable for sensitive skin?",
    "Where can I buy authentic product in UAE?"
  ],
  "conversion_angles": [
    "Why {product_context['product_name']} is worth the premium price",
    "{product_context['product_name']} vs cheaper dupes: what you're actually paying for",
    "5 reasons {product_context['product_name']} beats [competitor]"
  ]
}}

RETURN ONLY VALID JSON. NO MARKDOWN, NO EXPLANATION."""
    
    return prompt