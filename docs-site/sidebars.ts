import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  userGuideSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'user-guide/overview',
        'user-guide/getting-started',
        'user-guide/end-to-end-workflow',
        'user-guide/quick-reference',
        'user-guide/creating-estimates',
      ],
    },
    {
      type: 'category',
      label: 'Compute Workloads',
      collapsed: false,
      items: [
        'user-guide/workloads',
        'user-guide/jobs-compute',
        'user-guide/all-purpose-compute',
        'user-guide/dlt-pipelines',
        'user-guide/dbsql-warehouses',
      ],
    },
    {
      type: 'category',
      label: 'AI/ML & Data Services',
      collapsed: false,
      items: [
        'user-guide/model-serving',
        'user-guide/vector-search',
        'user-guide/fmapi-databricks',
        'user-guide/fmapi-proprietary',
        'user-guide/lakebase',
        'user-guide/databricks-apps',
        'user-guide/ai-parse',
        'user-guide/shutterstock-imageai',
      ],
    },
    {
      type: 'category',
      label: 'Features',
      collapsed: false,
      items: [
        'user-guide/ai-assistant',
        'user-guide/exporting',
        'user-guide/calculation-reference',
        'user-guide/faq',
      ],
    },
  ],
  adminGuideSidebar: [
    {
      type: 'category',
      label: 'Admin Guide',
      collapsed: false,
      items: [
        'admin-guide/deployment',
        'admin-guide/configuration',
        'admin-guide/database',
        'admin-guide/api-reference',
        'admin-guide/troubleshooting',
        'admin-guide/architecture',
        'admin-guide/installer',
        'admin-guide/permissions',
      ],
    },
  ],
  testingGuideSidebar: [
    {
      type: 'category',
      label: 'Testing Guide',
      collapsed: false,
      items: [
        'testing/overview',
        'testing/parity-tests',
        'testing/jobs-workload-tests',
        'testing/allpurpose-compute-tests',
        'testing/dlt-calculation-tests',
        'testing/dlt-ai-tests',
        'testing/dbsql-ai-tests',
        'testing/model-serving-ai-tests',
        'testing/vector-search-ai-tests',
        'testing/fmapi-databricks-ai-tests',
        'testing/fmapi-proprietary-ai-tests',
        'testing/lakebase-excel-tests',
        'testing/multi-workload-ai-tests',
        'testing/ml-pipeline-ai-tests',
        'testing/installation-tests',
        'testing/integration-validation-tests',
      ],
    },
  ],
};

export default sidebars;
