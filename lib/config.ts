// Configuration file for API settings
import { systemPrompt } from './system-prompt';

export const config = {
  // Anthropic API Key - Replace with your actual API key
  anthropicApiKey: process.env.NEXT_PUBLIC_ANTHROPIC_API_KEY || "",

  // OpenAI API Key - Replace with your actual API key
  openaiApiKey: process.env.DATABRICKS_TOKEN || "",

  // OpenAI Base URL (optional) - for custom endpoints like Azure OpenAI or Databricks
  openaiBaseUrl: process.env.NEXT_PUBLIC_OPENAI_BASE_URL || "https://e2-demo-field-eng.cloud.databricks.com/serving-endpoints",

  // Python executable path - defaults to 'python3', can be overridden with env var
  pythonPath: process.env.PYTHON_PATH || "python3",

  // System prompt that will be prepended to user input
  systemPrompt: systemPrompt,
};
