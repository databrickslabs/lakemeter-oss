// Configuration file for API settings
import { systemPrompt } from './system-prompt';

export const config = {
  // Anthropic API Key - Replace with your actual API key
  anthropicApiKey: process.env.NEXT_PUBLIC_ANTHROPIC_API_KEY || "",

  // OpenAI API Key - Replace with your actual API key
  openaiApiKey: process.env.DATABRICKS_TOKEN || "",

  // OpenAI Base URL (optional) - for custom endpoints like Azure OpenAI or Databricks
  openaiBaseUrl: process.env.OPENAI_BASE_URL || "https://e2-demo-field-eng.cloud.databricks.com/serving-endpoints",

  // OpenAI Model - defaults to 'databricks-gpt-5-1', can be overridden with env var
  openaiModel: process.env.OPENAI_MODEL || "ka-5cb2e157-endpoint", // "databricks-gpt-5-1",

  // Use responses API - if true, use client.responses.create instead of client.chat.completions.create
  useResponsesApi: process.env.USE_RESPONSES_API === "true" || true,

  // Python executable path - defaults to 'python3', can be overridden with env var
  pythonPath: process.env.PYTHON_PATH || "python3",

   // Default Catalog
  lakemeterCatalog: process.env.CATALOG || "users",

  // Default Schema
  lakemeterSchema: process.env.SCHEMA || "fajar_muharandy",

  // System prompt that will be prepended to user input
  systemPrompt: systemPrompt,
};
