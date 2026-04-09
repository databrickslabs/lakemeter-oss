# Lakemeter Salesforce Table

This folder defines all source code for the 'Lakemeter Salesforce Table' pipeline:

- `explorations`: Ad-hoc notebooks used to explore the data processed by this pipeline.
- `transformations`: All dataset definitions and transformations.

## Getting Started

To get started, go to the `transformations` folder -- most of the relevant source code lives there:

* By convention, every dataset under `transformations` is in a separate file.
* Take a look at the sample under "sample_users_lakemeter_salesforce_table.sql" to get familiar with the syntax.
  Read more about the syntax at https://learn.microsoft.com/azure/databricks/ldp/developer/sql-ref.
* Use `Run file` to run and preview a single transformation.
* Use `Run pipeline` to run _all_ transformations in the entire pipeline.
* Use `+ Add` in the file browser to add a new data set definition.
* Use `Schedule` to run the pipeline on a schedule!

For more tutorials and reference material, see https://learn.microsoft.com/azure/databricks/ldp.
