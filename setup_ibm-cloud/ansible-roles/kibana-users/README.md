# Kibana Users Ansible Role

This Ansible role creates multiple Kibana users with developer permissions for Elasticsearch and Kibana. The users can create indices, use the Dev Tools UI, access Elasticsearch cluster health metrics, and use Kibana's Enterprise Search Web Crawler.

## Features

- **Web Crawler Support**: Users have full access to Kibana's Enterprise Search and Web Crawler features
- **Smart Updates**: Only updates existing users if their roles have changed, avoiding unnecessary modifications
- **Idempotent**: Safe to run multiple times - skips users that already exist with correct roles
- **Comprehensive Permissions**: Full access to Discover, Visualize, Dashboard, Dev Tools, and Enterprise Search

## Requirements

- Ansible 2.9 or higher and Python with `openpyxl` (used by `kibana_credentials.py` to read the Excel file). Both are installed by `uv sync` in the repository root
- Access to an Elasticsearch cluster with admin credentials
- Elasticsearch Security features enabled
- Kibana connected to the Elasticsearch cluster

## Role Variables

Available variables are listed below, along with default values (see `defaults/main.yml`):

### Elasticsearch Connection

```yaml
elasticsearch_host: "localhost"
elasticsearch_port: 9200
elasticsearch_protocol: "https"
elasticsearch_admin_user: "admin"
elasticsearch_admin_password: ""
```

### User Configuration

```yaml
# Excel workbook with the columns "Email", "Kibana User" and "Password" (one user per row).
# Create/fill it with: uv run python kibana_credentials.py generate <file.xlsx>
kibana_users_excel: ""   # e.g. -e kibana_users_excel=/path/to/students.xlsx
kibana_users_sheet: "Contacts"

# Prefix prepended to a "Kibana User" cell that only contains a number (3 -> kibana_user3)
kibana_user_prefix: "kibana_user"

# Role name for the users
kibana_user_role_name: "kibana_developer"
```
