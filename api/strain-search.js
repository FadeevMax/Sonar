export default async function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    const { query, conversation_history = [] } = req.body;

    if (!query) {
      res.status(400).json({ error: 'Query is required' });
      return;
    }

    console.log('Processing query:', query);

    // Get Perplexity API key
    const apiKey = process.env.PERPLEXITY_API_KEY;
    console.log('API key exists:', !!apiKey);

    if (!apiKey) {
      res.status(500).json({ 
        error: 'API key not configured',
        response: getFallbackResponse(query),
        status: 'fallback'
      });
      return;
    }

    // Call Perplexity API
    const response = await fetch('https://api.perplexity.ai/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'sonar-small',
        messages: [
          {
            role: 'system',
            content: `You are a cannabis industry research assistant powered by Perplexity AI tools. Your role is to help report on strain-specific data points. You will be provided with the name of a cannabis strain. Your task is to return a structured report containing 14 specific data fields, all in plain text Markdown format, as outlined below.

### If the strain is well-known
If the strain is established and information is available, conduct intelligent research using all tools at your disposal. Cross-reference reputable sources (Leafly.com (primary), CannaDB.org, Strainsdb.org, etc.) to ensure accuracy. Return the most up-to-date and complete information for the following 14 fields:

---

1. **Strain Name**
2. **Alt Name(s)**
3. **Nickname(s)**
4. **Hybridization** (Indica, Sativa or Hybrid)
5. **Lineage/Genetics**
6. **Trivia** (Interesting facts about the strain)
7. **Reported Flavors (Top 3)**
8. **Reported Effects (Top 3)**
9. **Availability by State (U.S. states where it's sold)**
10. **Awards (if any)**
11. **Original Release Date (if known)**
12. **Physical Characteristics (Color, Bud Structure, Trichomes)**
13. **Similar Strains (Top 3 by effect/genetics)**
14. **User Rating (Average Score, # of Reviews, Common Comments)**

---
### If the strain is a new hybrid and/or information is limited

If full information is not available about the strain (e.g., it's a new hybrid or rare cross). Clearly state that the original strain had insufficient data.

---

### Tone and format

- Professional, neutral, data-focused.
- Use **bullet points or line breaks** where appropriate for readability.
- If a data point is **unknown or unavailable**, state: "Unknown".

---
**(Example for a Successful Primary Search)**

**User input:** "gg #4"

**Example Output:**  

**Strain Name:** GG #4

**Alt Name(s):** Original Glue, Gorilla Glue #4, Glue

**Nickname(s):** GG4, The Glue, Couch-Glue

**Hybridization:** Hybrid

**Lineage / Genetics:** Chem’s Sister × Sour Dubb × Chocolate Diesel (phenotype #4 selected by Joesy Whales & Lone Watie of GG Strains)

**Trivia (Interesting Facts):**
- Discovered accidentally when a hermaphroditic Chem’s Sister pollinated Sour Dubb plants; the keeper seed became phenotype #4—hence “#4” in the name.
- Named “Gorilla Glue” for the ultra-sticky resin that “glued” trimming scissors together during harvest.
- Forced to rebrand as “Original Glue / GG4” after trademark litigation with Gorilla Glue adhesive company (2017).

**Reported Flavors:**
- Earthy / Pungent Diesel
- Pine & Hash Spice
- Chocolate / Coffee undertone

**Reported Effects:**
- Heavy euphoria → deep relaxation (“couch-lock”)
- Sleepiness & hunger
- Mood elevation / stress relief

**Availability by State:** Widely distributed; regularly stocked in adult-use or medical markets including CA, CO, NV, WA, OR, MI, MA, IL, AZ, OK, NJ, NY and many others.

**Awards:**
- 1st Place Hybrid – High Times Cannabis Cup Michigan 2014
- 1st Place Hybrid – High Times Cannabis Cup Los Angeles 2014
- 1st Place – High Times World Cup Jamaica 2015

**Original Release Date:** Phenotype selected and released to market circa 2013; major Cup wins in 2014 established popularity.

**Physical Characteristics (Color, Bud Structure, Trichomes):**
- Dense, medium-green buds with lime & olive hues
- Thick blanket of milky trichomes giving a silvery-white frost
- Sparse but vivid orange pistils
- Extremely sticky resin glands (scissor-clogging).

**Similar Strains:**
- GG #5 (Sister Glue) – same breeding program
- Chem D – shared Chemdawg lineage / pungent diesel profile
- Sour Diesel – similar sour-fuel aroma and uplifting head rush

**User Rating:**
- Leafly average: 4.6 / 5 from 5,400 + user reviews
- Common remarks: “instant head euphoria then body melt,” “sticky buds,” strong relief for stress, pain, insomnia; some note dry mouth & anxious onset at high doses.

---
**(Example for a Fallback Scenario)**

Insufficient data for strain 'Galactic Runtz'. Contact web@headquarters.co`
          },
          ...conversation_history.slice(-5),
          {
            role: 'user',
            content: query
          }
        ],
        max_tokens: 2000,
        temperature: 0.2,
        top_p: 0.9
      })
    });

    console.log('Perplexity API status:', response.status);

    if (response.ok) {
      const result = await response.json();
      const content = result.choices[0].message.content;
      
      res.status(200).json({
        response: content,
        status: 'success'
      });
    } else {
      const errorText = await response.text();
      console.log('Perplexity API error:', errorText);
      
      res.status(200).json({
        response: getFallbackResponse(query),
        status: 'fallback'
      });
    }

  } catch (error) {
    console.error('Handler error:', error);
    res.status(200).json({
      response: getFallbackResponse(req.body?.query || 'strain'),
      status: 'error'
    });
  }
}

function getFallbackResponse(query) {
  return `🔍 **Searching for: ${query}**

I'm currently having trouble accessing the strain database, but I can provide some general guidance:

**For strain research, typically look for:**
• **Genetics & Lineage** - Parent strains and breeding history
• **Cannabinoid Profile** - THC/CBD percentages and ratios  
• **Effects** - Physical and mental experiences reported

**Popular strain categories:**
• **Sativa** - Often energizing, creative, daytime use
• **Indica** - Typically relaxing, sedating, evening use  
• **Hybrid** - Balanced effects from both types

Please try your search again in a moment!

*Note: This information is for educational purposes only.*`;
}