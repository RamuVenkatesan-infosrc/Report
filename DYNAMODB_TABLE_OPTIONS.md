# DynamoDB Table Design Options

## Current Implementation: Single Table Design ✅

### Table Name: `api-performance-analysis`
All analysis types stored in the SAME table, differentiated by `analysis_type` field.

**Benefits**:
- ✅ Already created and working
- ✅ Simple to maintain
- ✅ Easy cross-type queries
- ✅ Uses existing table structure

## Option 1: Keep Single Table (Recommended)

### Current Setup
```
Table: api-performance-analysis
Primary Key: 
  - Partition Key: analysis_id
  - Sort Key: analysis_type

Values for analysis_type:
- "report_analysis" → Performance report analysis
- "full_repository_analysis" → Full repository analysis
- "api_performance_matching" → API performance matching
```

**Query Examples**:
```python
# Get all analyses (any type)
all_analyses = scan_table()

# Get only report analyses
report_analyses = query(analysis_type="report_analysis")

# Get only GitHub analyses
github_analyses = scan(analysis_type IN ["full_repository_analysis", "api_performance_matching"])
```

## Option 2: Create Separate Tables

If you prefer separate tables for different analysis types:

### Tables Needed:
1. `api-performance-analysis` - For report analysis (already exists)
2. `github-analysis-results` - For all GitHub analyses

### Schema for New Table

```python
Table Name: github-analysis-results
Primary Key:
  - Partition Key: analysis_id (String)
  - Sort Key: analysis_type (String)

Values for analysis_type:
- "full_repository_analysis"
- "api_performance_matching"

GSI:
- timestamp-index (on timestamp field)
```

## Comparison

| Feature | Single Table | Separate Tables |
|---------|-------------|-----------------|
| **Setup Complexity** | ✅ Simple (already done) | ❌ Needs new table |
| **Query Complexity** | ⚠️ Need filtering | ✅ Direct query |
| **Maintenance** | ✅ One table to manage | ❌ Multiple tables |
| **Cost** | ✅ Lower | ❌ Higher |
| **Cross-type Queries** | ✅ Easy | ❌ More complex |
| **Schema Flexibility** | ⚠️ Same schema for all | ✅ Different schemas |

## Recommendation

**Keep the Single Table Design** because:
1. ✅ Already implemented and working
2. ✅ Simpler to manage
3. ✅ Lower cost
4. ✅ Better for cross-analysis queries
5. ✅ Uses your existing table

## Which Option Do You Prefer?

Please let me know if you want to:
- **Option A**: Keep single table (current implementation) ✅
- **Option B**: Create separate table for GitHub analysis

If you choose Option B, I can:
1. Create a new DynamoDB table
2. Update the code to use separate storage
3. Migrate existing data if needed

