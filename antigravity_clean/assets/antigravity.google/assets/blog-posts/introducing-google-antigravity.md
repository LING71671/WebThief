---
slug: introducing-google-antigravity
categories:
  - Product
author: The Antigravity Team
authorTitle: 
date: 2025-11-18T18:19:47.807Z
title: Introducing Google Antigravity, a New Era in AI-Assisted Software Development
articleImage: blog/blog-introducing-google-antigravity.png
---

Every advancement in model intelligence for coding has encouraged us to rethink how development should be done. The Integrated Development Environment (IDE) of today is a far cry from the IDE of just a few years ago. Gemini 3, our most intelligent model, represents a step-change for agentic coding, and requires us to think about what the next step-change of an IDE should be. 

Today, we are introducing Google Antigravity, our new agentic development platform. While the core is a familiar AI-powered IDE experience with the best of Googleâ€™s models, Antigravity is evolving the IDE towards an agent-first future with browser control capabilities, asynchronous interaction patterns, and an agent-first product form factor that together, enable agents to autonomously plan and execute complex, end-to-end software tasks.

## Why We Built Antigravity
We want Antigravity to be the home base for software development in the era of agents. Our vision is to ultimately enable anyone with an idea to experience liftoff and build that idea into reality. From today, Google Antigravity is available in public preview at no charge, with generous rate limits on Gemini 3 Pro usage. 

With models like Gemini 3, we have started hitting the point in agentic intelligence where models are capable of running for longer periods of time without intervention across multiple surfaces. Not yet for days at a time without intervention, but weâ€™re getting closer to a world where we interface with agents at higher abstractions over individual prompts and tool calls. In this world, the product surface that enables communication between the agent and user should look and feel different - and Antigravity is our answer to this.

## Core Tenets
Antigravity is our first product that brings four key tenets of collaborative development together: trust, autonomy, feedback, and self-improvement.

### Trust
Most products today live in one of two extremes: either they show the user every single action and tool call the agent has made or they only show the final code change with no context on how the agent got there, and with no easy way to verify the work. Neither engenders user trust in the work that the agent undertook. Antigravity provides context on agentic work at a more natural task-level abstraction, with the necessary and sufficient set of artifacts and verification results, for the user to gain that trust. There is a concerted emphasis for the agent to thoroughly think through verification of its work, not just the work itself.

In a conversation with an agent in Antigravity, the user sees tool calls grouped within tasks, monitoring high level summaries and progress along that task. As the agent works, it produces Artifacts, tangible deliverables in formats that are easier for users to validate than raw tool calls, such as task lists, implementation plans, walkthroughs, screenshots, and browser recordings.  Agents in Antigravity use Artifacts to communicate to the user that it understands what it is doing and that it is thoroughly verifying its work.

{{video: https://www.youtube.com/embed/6QeVnO709r0?si=Wdrd2haIwDE1MMSe, blog/introducing-antigravity-1.jpg, View the Agent's task list, review the implementation plan post-research and pre-implementation, or scan the walkthrough at completion.}}

### Autonomy
Today, the most intuitive product form factor is working synchronously with an agent embedded within a surface (an editor, browser, terminal, etc). That is why Antigravityâ€™s primary â€œEditor viewâ€ is a state-of-the-art AI-powered IDE experience, with Tab completions, in-line Commands, and a fully functioning agent in the side panel. 

That being said, we are transitioning to an era, with models like Gemini 3, when agents can operate across all of these surfaces simultaneously and autonomously: 

{{video: https://www.youtube.com/embed/HRH4kUlMeAM?si=Wdrd2haIwDE1MMSe, blog/introducing-antigravity-2.jpg, Autonomously, an Antigravity Agent writes code for a new frontend feature, uses the terminal to launch localhost, and actuates the browser to test that the new feature works.}}

We also believe agents deserve a form factor that exposes this autonomy optimally and allows users to interact with them more asynchronously. So, in addition to the IDE-like Editor surface,  we are introducing an agent-first Manager surface, which flips the paradigm of agents being embedded within surfaces to one where the surfaces are embedded into the agent. You can think of it like a mission control for spawning, orchestrating, and observing multiple agents across multiple workspaces in parallel. 

{{video: https://www.youtube.com/embed/JG28VZRHRe0?si=Wdrd2haIwDE1MMSe, blog/introducing-antigravity-3.jpg, User spawned an Agent to do background research in a different workspace while focusing on a more involved task in the foreground, using the Inbox and side panel in the Agent Manager to be notified of progress.}}

We decided not to try to squeeze both the asynchronous Manager experience and the synchronous Editor experience into a single window, rather optimizing for instantaneous handoffs between the Manager and Editor. Antigravity is designed to be forward-looking, intuitively bringing development to the asynchronous era as models like Gemini continue to rapidly get smarter. 

### Feedback
A core failing of a remote-only form factor is the inability to iterate easily with the agent. Agentic intelligence has indeed improved significantly, but it is still not perfect. An agent being able to complete 80% of the work should be useful, but if there is no easy way to provide feedback, then it becomes more work than benefit to resolve the remaining 20%. User feedback allows us to not treat an agent as a black-or-white system that either is perfect or unhelpful. Antigravity is starting with local operation, allowing intuitive async user feedback across every surface and Artifact, whether it be Google-doc-style comments on text Artifacts or select-and-comment feedback on screenshots. This feedback will be automatically incorporated into the agentâ€™s execution without requiring you to stop the agentâ€™s process. 

{{video: https://www.youtube.com/embed/WpjiSzypOkY?si=Wdrd2haIwDE1MMSe, blog/introducing-antigravity-4.jpg, An example of feedback on textual Artifacts such as an implementation plan and an example of feedback on a visual Artifact such as a screenshot taken by the Agent.}}

### Self-improvement
Antigravity treats learning as a core primitive, with agent actions both retrieving from and contributing to a knowledge base. This knowledge management allows the agent to learn from past work. This could be important explicit information such as useful snippets of code or derived architecture, but could also be more abstract, such as the series of steps taken to successfully complete a particular subtask.

{{video: https://www.youtube.com/embed/tB7flTt8A1E?si=Wdrd2haIwDE1MMSe, blog/introducing-antigravity-5.jpg, Agent learning from work and feedback to generate and leverage knowledge items, viewable from the Agent Manager.}}

## Try Antigravity Today
We believe Antigravityâ€™s product form factor represents the next fundamental step function in agent-assisted development. Thus, our goal is to channel it into the best product offering possible for end users. In todayâ€™s public preview:

- Google Antigravity for individuals at no charge 
- Compatibility with MacOS, Linux, and Windows
- Access to Googleâ€™s Gemini 3, Anthropicâ€™s Claude Sonnet 4.5 models, and OpenAIâ€™s GPT-OSS within the agent, offering developers model optionality [^rate-limits]

Learn more about the features of Antigravity in [our docs](/docs) and read more about how Antigravity can assist you by browsing various [use cases](/use-cases). We will have new features dropping frequently, so keep up-to-date with this blog and socials at [X](https://x.com/antigravity), [LinkedIn](https://linkedin.com/company/google-antigravity), and [YouTube](https://youtube.com/@GoogleAntigravity).

Experience liftoff in 3â€¦ 2â€¦ 1â€¦

{{button: Download Antigravity, /download}}

[^rate-limits]: [1] We will be providing access to models to the degree we have capacity, with rate limits to prevent abuse and that are refreshed every five hours. Under the hood, the rate limits are correlated with the amount of work done by the agent, which can differ from prompt to prompt. Thus, you may get many more prompts if your tasks are more straightforward and the agent can complete the work quickly, and the opposite is also true. Our modeling suggests that a very small fraction of power users will ever hit the per-five-hour rate limit, so our hope is that this is something that you wonâ€™t have to worry about, and you feel unrestrained in your usage of Antigravity.
