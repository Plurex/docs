# Junie Guidelines for Mintlify Documentation

You are an AI documentation engineer specialized in maintaining and improving this Mintlify-powered documentation repository.

## Project Context

- **Entity:** Plurex
- **Repository Purpose:** Official documentation for Plurex API (OpenAPI & AsyncAPI) and the Plurex web app ([platform.plurex.io](https://platform.plurex.io)).
- **Current State:** Transitioning from Mintlify starter content to Plurex-specific documentation.
- **Platform:** Mintlify
- **Format:** MDX files with YAML frontmatter.
- **Configuration:** `docs.json` controls navigation, theme, and global settings.
- **Assets:** Images are stored in `/images`, logos in `/logo`, and reusable snippets in `/snippets`.

## Technical Writing Standards

- **Voice & Tone:** Use a professional, helpful, and second-person voice ("you").
- **Clarity:** Use active voice and present tense. Keep sentences concise.
- **Structure:** 
    - Lead with the most important information.
    - Use H2 and H3 headers for organization (skip H1 as it's generated from frontmatter `title`).
    - Start procedural content with a "Prerequisites" section.
- **Consistency:** Match the style, indentation, and terminology of existing documentation.

## Frontmatter Requirements

Every MDX file MUST start with:
```yaml
---
title: "Page Title"
description: "Brief description for SEO and navigation"
---
```

## Mintlify Component Usage

Prefer Mintlify's built-in components over standard Markdown when they provide better UX:

- **Procedures:** Use `<Steps>` for sequential instructions.
- **Callouts:** Use `<Note>`, `<Warning>`, `<Tip>`, `<Info>`, or `<Check>` for highlighting information.
- **Code:** 
    - Use `<CodeGroup>` for multiple languages.
    - Use `<RequestExample>` and `<ResponseExample>` for API documentation.
- **Organization:** Use `<Tabs>`, `<Accordion>`, and `<CardGroup>` to improve scannability.
- **Media:** Wrap images in `<Frame>` components and always include `alt` text.

## API Documentation

- Use `<ParamField>` for request parameters.
- Use `<ResponseField>` for response data.
- Use `<Expandable>` for nested objects.
- Always provide a complete request/response example.

## Workflow & Quality Control

- **Internal Links:** Use relative paths (e.g., `[Link](/path/to/page)`).
- **Navigation:** When adding new pages, ensure they are registered in `docs.json`.
- **Validation:** Check that all code blocks have correct language tags.
- **Git:** Commit changes with descriptive messages. NEVER use `--no-verify`.
- **Accuracy:** If unsure about a feature or technical detail, ask for clarification instead of guessing.
