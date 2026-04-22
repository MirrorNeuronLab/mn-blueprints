# General Openshell LLM Codegen

This blueprint demonstrates an advanced multi-agent workflow using MirrorNeuron and OpenShell to perform safe, iterative Large Language Model (LLM) code generation and validation.

## What it does

This workflow represents a complex self-improving loop:

1. **Iterative Generation and Review**: The pipeline executes three distinct rounds of code generation and review.
   - An LLM agent (`codegen`) writes Python code based on the initial requirements or previous reviews.
   - A secondary LLM agent (`review`) acts as a strict code reviewer, analyzing the generated code and providing concrete suggestions and identifying risks.
   - This creates an adversarial, multi-shot improvement process.
2. **Tool Creation**: The AI is tasked with solving an interesting problem that requires it to not just use standard libraries, but actually **build a new tool during runtime**. It dynamically generates a bash script to handle log filtering using standard Unix tools (`grep`/`awk`) and then executes it to assist its own Python logic.
3. **Isolated Sandbox Validation**: Finally, the `validator` node executes the LLM-generated code against test cases. Because LLM output is unpredictable and executing it directly on a host machine is dangerous, all nodes (including the LLM processing nodes and the final validator) run inside isolated **OpenShell Sandboxes**.
   - Network egress is explicitly restricted to only allow outbound traffic to Google's API endpoints via the `api-egress.yaml` policy.
   - The validation phase asserts that the dynamically generated helper bash script was created correctly, and that the code outputs the expected results.

## Why it's important

This blueprint showcases:
- **Safety**: Untrusted, LLM-generated code is executed inside a fully isolated OpenShell container, preventing host machine contamination.
- **Resilience**: The iterative review rounds give the LLM multiple chances to refine complex logic before it hits final validation.
- **Dynamic Capabilities**: It demonstrates the AI acting as a tool-maker, rather than just a tool-user, extending its own capabilities dynamically.
