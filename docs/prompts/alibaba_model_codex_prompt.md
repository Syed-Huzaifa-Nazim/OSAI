# Codex Prompt: Prepare and Train an Alibaba B2B Analysis Model

Please inspect the existing **Daraz model folder** and its ZIP file. Analyze the project files and all CSV and Excel (`.xlsx`) datasets to understand how the Daraz B2C data is structured, prepared, and used to train the model.

We now want to build a similar analysis and training workflow for our **Alibaba ecommerce model**, using the data we scrape for Alibaba. Alibaba is a B2B platform, while Daraz and its dataset are B2C, so the existing dataset may not match Alibaba’s business model.

Use the Daraz dataset as a reference, then propose and prepare a separate Alibaba-oriented dataset by adapting its structure. Identify which columns should be retained, excluded, renamed, or added to better represent B2B products and transactions. Do not assume that every Daraz column has a suitable Alibaba equivalent.

## Goals

1. Inspect the Daraz model folder, ZIP archive, scripts, notebooks, documentation, and datasets.
2. Explain the Daraz workflow: data cleaning, feature selection, target definition, model training, evaluation, and outputs.
3. Inspect the available Alibaba scraped data and compare its fields with the Daraz dataset.
4. Prepare an Alibaba-oriented dataset and a repeatable preprocessing workflow that fits the available data and supports model training.
5. Train and evaluate an Alibaba model using the Daraz approach where it makes sense. Clearly explain any differences required by the B2B setting.
6. Document assumptions, transformations, limitations, and the final workflow.

## Decision checkpoints

Do not make major decisions without asking me first. Before taking a consequential step—such as choosing a new prediction target, dropping potentially useful data, making a substantial schema change, or changing the model approach—describe the options and ask me to decide. Continue with non-destructive inspection and reversible preparation while waiting for my decision.

Do not silently invent or derive B2B labels, such as supplier quality, demand, or product success, unless the available data supports them. Explain clearly when scraped fields are only proxies and what they can and cannot tell us.

## Recommendations

Share additional ideas and recommendations in a separate section. For each idea, briefly explain its expected benefit and any trade-offs so I can decide whether to use it.

## Git instructions

Do not commit or push anything to Git or GitHub unless I explicitly authorize it.

Do your best to complete the workflow, preserve the existing Daraz project, and make the Alibaba work easy to review and reproduce.
