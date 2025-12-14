# Lakemeter Base Environment Setup

This guide explains how to use the `lakemeter_base_environment.yml` file to automatically install dependencies in Databricks serverless notebooks.

## 📋 What is a Base Environment?

A **base environment** is a YAML file that specifies Python dependencies for Databricks serverless notebooks. By using a base environment, you can:

- ✅ **Eliminate `%pip install` commands** from notebooks
- ✅ **Standardize dependencies** across all team members
- ✅ **Speed up notebook startup** (dependencies are cached)
- ✅ **Version control** your environment

## 📦 Included Dependencies

The `lakemeter_base_environment.yml` includes:

| Package | Version | Purpose |
|---------|---------|---------|
| `psycopg2-binary` | 2.9.9 | PostgreSQL adapter for connecting to Lakebase |
| `pandas` | 2.1.4 | Data manipulation and analysis |
| `tabulate` | 0.9.0 | Pretty-print tabular data in console |

## 🚀 Quick Setup

### Step 1: Upload to Databricks Workspace

1. Go to your Databricks workspace
2. Navigate to: `/Workspace/Users/steven.tan@databricks.com/lakemeter/Lakebase_Setup/`
3. Upload `lakemeter_base_environment.yml` to this folder

### Step 2: Use in a Notebook

1. Open any serverless notebook (or connect to **Serverless** compute)
2. Click the **Environment** side panel (⚙️ icon on the right)
3. Under **Base environment**, select **Custom**
4. Click the folder icon 📁 to browse
5. Select `/Workspace/Users/steven.tan@databricks.com/lakemeter/Lakebase_Setup/lakemeter_base_environment.yml`
6. Click **Apply**
7. Wait for dependencies to install (first time only)

### Step 3: Remove `%pip install` Commands

Once the base environment is applied, you can **remove** these lines from your notebooks:

```python
# ❌ DELETE THIS:
%pip install psycopg2-binary pandas tabulate
dbutils.library.restartPython()
```

The dependencies are already installed via the base environment!

## 🔄 Updating the Test Notebooks

All test notebooks (Test_01 through Test_14) currently have:

```python
%pip install psycopg2-binary pandas tabulate
dbutils.library.restartPython()
```

**After applying the base environment, you can remove these lines!**

## 💾 Alternative: Unity Catalog Volume (Recommended for Production)

For better sharing across the workspace:

1. Upload to a Unity Catalog volume:
   ```
   /Volumes/main/lakemeter/environments/lakemeter_base_environment.yml
   ```

2. In notebooks, select **Custom** base environment and use the volume path

3. All users with access to the volume can use the same environment

## 🔍 Viewing Installed Dependencies

To verify dependencies are installed:

1. Open the **Environment** side panel
2. Click the **Installed** tab
3. You should see:
   - `psycopg2-binary==2.9.9`
   - `pandas==2.1.4`
   - `tabulate==0.9.0`

4. Click **pip logs** at the bottom to see installation logs

## 🔄 Resetting the Environment

If something goes wrong:

1. Click the **Environment** side panel
2. Click the arrow next to **Apply**
3. Select **Reset to defaults**
4. Reapply the base environment

## 📝 Adding More Dependencies

To add more dependencies to the base environment:

1. Edit `lakemeter_base_environment.yml`
2. Add packages under `dependencies: - pip:`
3. Re-upload to Databricks
4. In notebooks, click **Apply** again to reload

Example:

```yaml
dependencies:
  - pip:
      - psycopg2-binary==2.9.9
      - pandas==2.1.4
      - tabulate==0.9.0
      - sqlalchemy==2.0.23  # NEW!
      - requests==2.31.0    # NEW!
```

## 🎯 Benefits for Lakemeter Project

1. **Faster Test Execution**: No need to reinstall packages every time
2. **Consistent Environment**: All test notebooks use the same versions
3. **Easier Onboarding**: New team members just apply the base environment
4. **Version Control**: Environment is tracked in Git
5. **Cleaner Notebooks**: No installation commands cluttering the code

## 📚 Reference

- [Databricks Serverless Environment Documentation](https://docs.databricks.com/aws/en/compute/serverless/dependencies#-add-dependencies-to-a-base-environment)
- [Configure Serverless Environments](https://docs.databricks.com/aws/en/compute/serverless/dependencies.html)

## ⚠️ Important Notes

- **DO NOT** install PySpark or any library that depends on PySpark (it's already available)
- Base environment dependencies are **cached** across notebook sessions
- If you update a custom package, **increment its version number** for jobs to pick up changes
- The base environment applies only when connected to **Serverless** compute

## 🏁 Next Steps

1. Upload `lakemeter_base_environment.yml` to your Databricks workspace
2. Apply it to one test notebook (e.g., Test_01)
3. Remove the `%pip install` commands
4. Verify the notebook runs correctly
5. Apply to all other test notebooks

---

**Created for:** Lakemeter Q4 FY 2026 Team Project  
**Last Updated:** December 2025  
**Maintained by:** Database Backend Team

