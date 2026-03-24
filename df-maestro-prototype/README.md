# 🔗 Workflow Variable Prototype

> A product concept exploring native typed-variable access 
> to external data records inside workflow automation tools.

🔗 [Live Prototype](https://df-variablle-maestro.lovable.app) ← requires access

---

## The Problem

Modern workflow automation tools handle simple variables well:
```
string name = "Ishan"
number age = 35
json config = { "key": "value" }
```

But enterprise workflows constantly work with **structured records** 
from external systems — CRM accounts, ERP orders, database rows.

Today's approach is broken:
```
Step 1: Add "Query Record" activity → fetch customer from DB
Step 2: Store result in generic JSON variable
Step 3: Access fields with string keys → myVar["customer_name"]
Step 4: Customer updated mid-process?
Step 5: Add ANOTHER "Query Record" activity to refresh
Step 6: Repeat every time you need fresh data
```

**Problems with this:**
- Feels unnatural — data access is a "task" not a "variable"
- No type safety — field names are strings, typos break at runtime
- Stale data — records don't refresh automatically mid-process
- Poor developer experience — verbose, repetitive, error-prone
- Breaks the mental model — developers think in variables, not activities

This is not unique to one platform. It affects every B2B SaaS 
workflow tool that connects to external data — Salesforce Flow, 
HubSpot Workflows, Microsoft Power Automate, UiPath, Zapier, n8n.

---

## The Concept: Data-Bound Variables

What if external records behaved like native typed variables?
```
// Declare a variable bound to a table + record
DataRecord<Customer> myCustomer = bind(CustomerTable, recordId)

// Access fields with full type safety + autocomplete
string name = myCustomer.firstName        ✅ typed
number value = myCustomer.annualRevenue   ✅ typed  
date renewal = myCustomer.renewalDate     ✅ typed

// Inline operations — no separate activity needed
myCustomer.status = "Active"              ✅ updates the record
myCustomer.refresh()                      ✅ fetches latest data

// No more query activities. No more stale data.
// Just variables — the way developers already think.
```

**Key properties:**

| Property | Old approach | New concept |
|---|---|---|
| Data access | Query activity (a task) | Variable declaration (native) |
| Type safety | None — generic JSON | Strongly typed — IDE autocomplete |
| Data freshness | Stale — manual refresh | Bindable — refresh on demand |
| Field access | `record["field_name"]` (string) | `record.fieldName` (typed) |
| Updates | Separate update activity | Inline assignment |
| Developer experience | Verbose + error-prone | Natural + familiar |

---

## Why This Matters

**For developers building workflows:**
- Faster to write — IDE autocomplete shows all available fields
- Safer — type errors caught at design time, not runtime
- More readable — `customer.renewalDate` vs `getField(record, "renewal_date")`

**For the platform:**
- Reduces support tickets — fewer runtime errors from string typos
- Increases adoption — lower learning curve for developers
- Differentiates — most competitors still use the old activity model

**For the business:**
- Faster customer onboarding — less time learning the platform
- Higher NPS — better developer experience = happier customers
- Competitive moat — native data binding is hard to replicate quickly

---

## The Prototype

Built with Lovable (AI-powered React app builder) to validate 
the concept and get early feedback from engineering and customers.

**What the prototype demonstrates:**

1. **Variable declaration UI** — create a typed variable bound 
   to a table and record
2. **Field browser** — see all available fields with their types
3. **Inline operations** — read and write fields directly
4. **Type indicators** — visual cues for string/number/date/boolean fields

**This is a concept prototype — not production code.**  
Built to answer: *"Does this feel more natural than query activities?"*

---

## PM Process

**Problem discovery:**
Observed developers consistently struggling with data access patterns 
in workflow tools. The "query activity" model creates friction at 
every step — declaration, access, update, refresh.

**Insight:**
Every developer already knows how to work with variables. The 
mental model is universal. The gap is that external data records 
don't behave like variables — they behave like API calls wrapped 
in activities.

**Hypothesis:**
If external records behaved like typed variables, developer 
experience would improve measurably — fewer errors, faster 
development, higher satisfaction.

**Validation approach:**
Build a low-fidelity prototype → show to 5 developers → 
measure: does this feel more natural? Would you use this?

---

## Broader Applicability

This concept applies to any workflow tool that connects to 
external data:

| Platform | Current pain | Concept application |
|---|---|---|
| Salesforce Flow | Generic sObject variables | Typed record variables |
| Power Automate | Dynamic content picker | Bound typed variables |
| n8n | JSON dot notation | Schema-aware variables |
| Zapier | Field mapping dropdowns | Typed binding |
| HubSpot Workflows | Property string keys | Typed property access |

**The problem is industry-wide. The solution is universal.**

---

## What's Next (Product Roadmap Thinking)
```
Phase 1 — Read-only binding (MVP):
→ Declare variable bound to table + record
→ Access fields with type safety
→ Auto-refresh on read

Phase 2 — Write operations:
→ Inline field updates
→ Optimistic updates with rollback

Phase 3 — Collection variables:
→ Bind to query results (multiple records)
→ Iterate, filter, map — like arrays

Phase 4 — Cross-system binding:
→ Variable bound to Salesforce contact
→ Variable bound to SAP order
→ Same interface, any data source
```

---

## Built With

- **Lovable** — AI-powered React app prototyping
- **Concept design** — based on 11 years of B2B SaaS PM experience
- **Inspiration** — real developer pain observed across enterprise workflow platforms

---

*Built as part of a 15-day AI PM portfolio sprint.*  
*[github.com/ishannagar](https://github.com/ishannagar)*