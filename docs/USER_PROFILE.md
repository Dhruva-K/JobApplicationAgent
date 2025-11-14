# User Profile Management

## Overview

The user profile system has been consolidated into a single, comprehensive module with multiple interfaces.

## Structure

```
core/
  user_profile.py          # Core UserProfile class with all functionality
scripts/
  setup_profile.py         # Simple CLI for first-time profile creation
  manage_profile.py        # Full-featured profile management CLI
```

## UserProfile Class Methods

### Profile Management
- `create_profile()` - Create a new user profile
- `get_profile()` - Get profile by user_id
- `update_profile()` - Update profile fields
- `delete_profile()` - Delete a profile
- `list_all_profiles()` - List all profiles in system

### Skills Management
- `add_skill()` - Add a skill to profile
- `remove_skill()` - Remove a skill from profile
- `get_skills()` - Get all skills for a user

### Preferences
- `update_preferences()` - Update job search preferences
- `get_search_preferences()` - Get formatted preferences for job filtering

### Utilities
- `get_profile_summary()` - Get human-readable profile summary
- `interactive_setup()` - Static method for CLI-based profile creation

## Usage

### Quick Setup (First Time)
```bash
python setup_profile.py
```

Simple wizard for creating your first profile.

### Full Management
```bash
python manage_profile.py
```

Interactive menu with options:
1. Create new profile
2. View profile
3. List all profiles
4. Add skill
5. Remove skill
6. Update preferences
7. Delete profile
8. Exit

### Programmatic Usage

```python
from graph.memory import GraphMemory
from core.config import Config
from core.user_profile import UserProfile

# Initialize
config = Config()
neo = config.get_neo4j_config()
graph = GraphMemory(**neo)
user_profile = UserProfile(graph_memory=graph)

# Create profile
user_id = user_profile.create_profile(
    user_id="dhruva_001",
    name="Dhruva K",
    email="dhruva@example.com",
    skills=["python", "product management"],
    experience_years=2,
    education_level="Bachelor",
    preferences={
        "employment_types": ["INTERN", "FULLTIME"],
        "remote_only": False,
        "salary_min": 50000,
        "exclude_companies": ["Company X"]
    }
)

# Get search preferences (used by ScoutAgent)
prefs = user_profile.get_search_preferences(user_id)

# Add a skill
user_profile.add_skill(user_id, "data analytics")

# Update preferences
user_profile.update_preferences(user_id, {
    "remote_only": True,
    "salary_min": 60000
})

# Get summary
summary = user_profile.get_profile_summary(user_id)
print(f"Skills: {summary['skills']}")
```

## Profile Data Structure

### Stored in Neo4j User Node
```python
{
    "user_id": "dhruva_001",
    "name": "Dhruva K",
    "email": "dhruva@example.com",
    "experience_years": 2,
    "education_level": "Bachelor",
    
    # Job Search Preferences
    "employment_types": ["INTERN", "FULLTIME"],
    "remote_only": False,
    "preferred_locations": ["San Francisco", "New York"],
    "salary_min": 50000,
    "exclude_companies": ["Company X", "Company Y"]
}
```

### Skills (Separate Nodes)
```cypher
(:User {user_id: "dhruva_001"})-[:HAS_SKILL]->(:Skill {name: "python"})
(:User {user_id: "dhruva_001"})-[:HAS_SKILL]->(:Skill {name: "product management"})
```

## Integration with ScoutAgent

The profile system is fully integrated with the ScoutAgent for personalized job filtering:

```python
from agents.scout_agent import ScoutAgent

# Scout automatically uses profile preferences
scout.run(
    user_id="dhruva_001",
    keywords=None,  # Uses profile skills
    employment_type=None,  # Uses profile employment_types
    use_profile_filter=True
)
```

See `PROFILE_AWARE_SCOUT.md` for details on the filtering logic.

## No More Redundancy

✅ **Before**: `setup_profile.py` had duplicate logic
❌ **After**: All logic is in `UserProfile` class
- `setup_profile.py` → thin wrapper calling `UserProfile.interactive_setup()`
- `manage_profile.py` → full CLI using all `UserProfile` methods
- Both scripts share the same core functionality

## Benefits

1. **Single Source of Truth**: All profile logic in one class
2. **Reusable**: Use programmatically or via CLI
3. **Maintainable**: Changes to logic don't need script updates
4. **Testable**: Core class can be unit tested
5. **Extensible**: Easy to add new features
