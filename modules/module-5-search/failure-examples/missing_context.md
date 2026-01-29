# Failure: Missing Critical Context

## The Problem

The top-K setting is too low, causing the LLM to miss critical information needed for a complete answer.

## Example

**Query**: "Explain the complete working principle of a DC motor"

**top_k = 2** (INCOMPLETE):
```
Retrieved chunks:
1. "A DC motor works on the principle that a current-carrying conductor 
   placed in a magnetic field experiences a force."
2. "The direction of the force is given by Fleming's left-hand rule."

LLM Answer: "A DC motor works by the force on a current-carrying conductor 
in a magnetic field, following Fleming's left-hand rule."
```

Missing: back EMF, torque equation, commutator function, field types!

**top_k = 6** (COMPLETE):
```
Retrieved chunks:
1. "A DC motor works on the principle that a current-carrying conductor..."
2. "The direction of the force is given by Fleming's left-hand rule."
3. "Back EMF (Eb) is induced in the armature which opposes the supply voltage."
4. "Torque T = (ΦZI_a × P) / (2πA), where Φ is flux, Z is conductors..."
5. "The commutator converts AC induced in armature to DC at brushes..."
6. [Table: Types of DC motors - series, shunt, compound]

LLM Answer: "A DC motor converts electrical energy to mechanical energy 
through the interaction of magnetic fields. Key concepts include:
- Operating principle: Force on current-carrying conductor (Fleming's rule)
- Back EMF: Self-induced voltage opposing supply, Eb = V - IaRa
- Torque equation: T = kΦIa
- Commutator: Converts AC to DC, enables continuous rotation
- Types: Series (high starting torque), Shunt (constant speed), Compound..."
```

## Why It Happens

- Complex topics require multiple chunks for complete coverage
- Related information is spread across different sections
- Low top-K creates incomplete context windows

## The Fix

**Dynamic Top-K Based on Query Complexity**:

```python
def estimate_complexity(query: str) -> int:
    """Estimate query complexity to adjust top-K."""
    complexity_indicators = [
        "explain", "describe", "how does", "complete", 
        "all", "comprehensive", "detail"
    ]
    
    # Count indicators
    count = sum(1 for ind in complexity_indicators if ind in query.lower())
    
    # Base top-K with adjustment
    base_k = 4
    return min(base_k + count * 2, 10)  # Cap at 10

# Usage
top_k = estimate_complexity(query)
results = search(query, top=top_k)
```

**Check Context Coverage**:

```python
def check_coverage(results, expected_topics):
    """Verify that results cover expected topics."""
    combined_content = " ".join(r["content"] for r in results)
    
    missing = []
    for topic in expected_topics:
        if topic.lower() not in combined_content.lower():
            missing.append(topic)
    
    return missing

# For DC motor, expected: ["back emf", "torque", "commutator", "fleming"]
```

## Key Takeaway

> Start with top_k=5 as a baseline. Increase for complex "explain" questions. Monitor for incomplete answers and adjust accordingly.
