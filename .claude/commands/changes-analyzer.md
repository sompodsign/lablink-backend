# CHANGES-ANALYZER.md - Git Changes Analysis Command

Custom command for analyzing changes between master branch and current branch with intelligent insights.

## Command Definition

**`/changes-analyzer [flags]`**
```yaml
---
command: "/changes-analyzer"
category: "Analysis & Investigation"
purpose: "Analyze git changes between master and current branch with intelligent insights"
wave-enabled: false
performance-profile: "standard"
---
```

## Core Functionality

### Analysis Dimensions
1. **What Changed**: File-by-file diff analysis with context
2. **How It Works**: Technical implementation details and patterns
3. **Purpose Analysis**: Inferred business logic and feature intent
4. **Impact Assessment**: Affected systems and potential side effects

### Auto-Persona Activation
- **Primary**: Analyzer (systematic investigation)
- **Secondary**: Architect (system impact assessment)
- **Tertiary**: Domain-specific based on changed files

### MCP Integration
- **Sequential**: Complex change analysis and pattern recognition
- **Context7**: Framework pattern identification and best practices
- **Magic**: UI component change analysis (if applicable)

## Analysis Framework

### Change Classification
```yaml
addition: "New files, features, or functionality"
modification: "Updates to existing code or configuration"
deletion: "Removed files, functions, or features"
refactoring: "Code structure improvements without functional changes"
bugfix: "Error corrections and issue resolutions"
enhancement: "Improvements to existing functionality"
configuration: "Settings, environment, or build changes"
documentation: "Comments, README, or doc updates"
testing: "Test additions, modifications, or improvements"
```

### Technical Analysis Patterns
```yaml
database_changes:
  patterns: ["*.sql", "migrations/*", "models/*", "*schema*"]
  analysis: "Schema modifications, data flow, migration safety"
  
api_changes:
  patterns: ["*controller*", "*route*", "*endpoint*", "api/*"]
  analysis: "Contract changes, backward compatibility, integration impact"
  
frontend_changes:
  patterns: ["*.jsx", "*.tsx", "*.vue", "components/*", "pages/*"]
  analysis: "UI/UX modifications, user flow impact, accessibility"
  
backend_logic:
  patterns: ["*service*", "*business*", "*logic*", "*processor*"]
  analysis: "Business rule changes, data processing, workflow impact"
  
infrastructure:
  patterns: ["docker*", "*.yml", "*.yaml", "terraform/*", ".github/*"]
  analysis: "Deployment changes, environment impact, scaling considerations"
```

### Purpose Inference Engine
```yaml
feature_indicators:
  patterns: ["new", "add", "implement", "create", "introduce"]
  confidence: "high"
  
bugfix_indicators:
  patterns: ["fix", "resolve", "correct", "patch", "repair"]
  confidence: "high"
  
refactor_indicators:
  patterns: ["refactor", "cleanup", "improve", "optimize", "restructure"]
  confidence: "medium"
  
security_indicators:
  patterns: ["security", "auth", "permission", "validation", "sanitize"]
  confidence: "high"
  
performance_indicators:
  patterns: ["optimize", "cache", "index", "query", "performance"]
  confidence: "medium"
```

## Command Workflow

### Phase 1: Git Analysis
1. **Branch Comparison**: `git diff master...HEAD`
2. **Commit History**: `git log master..HEAD`
3. **File Statistics**: Added, modified, deleted files
4. **Change Scope**: Lines changed, complexity assessment

### Phase 2: Technical Analysis
1. **Pattern Recognition**: Identify change types and affected systems
2. **Framework Detection**: Technology stack and patterns used
3. **Dependency Analysis**: Impact on related components
4. **Integration Points**: API contracts, database schemas, configurations

### Phase 3: Purpose Analysis
1. **Commit Message Analysis**: Extract intent from commit history
2. **Code Pattern Analysis**: Infer purpose from implementation patterns
3. **Business Logic Mapping**: Connect technical changes to business value
4. **Risk Assessment**: Potential issues and mitigation strategies

### Phase 4: Report Generation
1. **Executive Summary**: High-level overview of changes
2. **Technical Details**: Implementation specifics and patterns
3. **Purpose Insights**: Inferred business requirements and goals
4. **Recommendations**: Testing, deployment, and monitoring suggestions

## Output Format

### Summary Section
```
📊 Changes Summary
- Files: X modified, Y added, Z deleted
- Lines: +XXX, -YYY
- Scope: [feature|bugfix|refactor|enhancement]
- Complexity: [low|medium|high]
```

### What Changed Section
```
🔍 What Changed
- Database: Schema modifications in user_profiles table
- API: New endpoint /api/v1/reports/service-importer
- Frontend: Updated dashboard component with new metrics
- Configuration: Added new environment variables
```

### How It Works Section
```
⚙️ How It Works
- Service Importer Integration: New report generation system
- Data Flow: user_request → service_api → data_processor → report_output
- Authentication: JWT validation with role-based access
- Caching: Redis implementation for report data (30min TTL)
```

### Purpose Analysis Section
```
🎯 Purpose Analysis
- Business Need: Customer requirement for service-specific reporting
- User Value: Faster report generation and better data visibility  
- Technical Debt: Addresses performance issues in legacy reporting
- Integration: Supports new partner API requirements
```

## Flags and Options

### Analysis Depth
- `--summary`: High-level overview only
- `--detailed`: Comprehensive analysis (default)
- `--technical`: Focus on implementation details
- `--business`: Focus on business impact and purpose

### Scope Control
- `--files [pattern]`: Analyze specific file patterns
- `--since [date]`: Changes since specific date
- `--author [name]`: Changes by specific author
- `--type [change-type]`: Focus on specific change types

### Output Control
- `--format [text|json|markdown]`: Output format
- `--export [path]`: Export analysis to file
- `--verbose`: Include detailed diff information

## Integration with SuperClaude

### Auto-Activation Triggers
- Keywords: "changes", "diff", "what changed", "compare branches"
- Git operations: When working with branches or preparing PRs
- Code review contexts: Pre-commit analysis and review preparation

### Persona Coordination
- **Analyzer**: Lead the investigation and pattern recognition
- **Architect**: Assess system-wide impact and design implications  
- **Security**: Evaluate security implications of changes
- **Performance**: Analyze performance impact of modifications
- **QA**: Identify testing requirements and risk areas

### Quality Gates
1. **Git Validation**: Ensure clean working directory and valid branch comparison
2. **Change Scope**: Verify changes are within reasonable complexity bounds
3. **Pattern Recognition**: Validate change classification accuracy
4. **Purpose Inference**: Cross-reference commit messages with code changes
5. **Impact Assessment**: Evaluate potential system-wide effects
6. **Report Quality**: Ensure comprehensive and actionable insights

## Example Usage

```bash
# Basic analysis
/changes-analyzer

# Detailed business-focused analysis
/changes-analyzer --detailed --business

# Technical analysis for specific files
/changes-analyzer --technical --files "*.sql,*controller*"

# Export comprehensive analysis
/changes-analyzer --export analysis.md --format markdown
```

## Integration Notes

- **Wave Mode**: Not typically needed due to focused scope
- **MCP Servers**: Sequential for analysis, Context7 for patterns
- **Performance**: Standard profile, <30 second analysis time
- **Quality**: Evidence-based insights with confidence scoring