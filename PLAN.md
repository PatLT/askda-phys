Agents for knowledge systemisation and discovery-by-analogy in physics = AKSDA-Phys

Inspired by reading Carlo Rovelli's book [[Helgoland]] - in which he points out that Mach's philosophy (late 19th c.) undergirded important discoveries in 20th c. physics including special relativity and quantum mechanics. And Nagarjuna's work provided and even earlier and more distant antecedent. 

An agentic discovery model composed of (in order):
1. **memeticist**. From a starting point on the knowledge web, assess each of its outward links for how close they cleave to being a single 'meme' of knowledge. 
2. **maniac**. Blue-sky researcher. Searches through corpus of human philosophy and draws analogies to concepts in physics. 
3. **interpreter**. Reviewer-1. Assesses these analogies for their novelty - in particular whether they just map to existing concepts in physics. Returns a score. 
4. **skeptic**. Reviewer-2. Assesses these analogies for their physical credibility. Returns a score. 
	* At this point, take average score and pass/fail the idea. If failed, it can still add into the web of knowledge. 
5. **supervisor_i**. Supervisor-1. Proposes a sub-field or closed-problem which the analogy maps onto. 
6. **junior**. Grad student. Attempts to systematize the analogy (uses phys-lean) to the proposed problem. 
7. **peer**. Reviewer-3. Assesses the formalism for success. 
8. **critic**. Reviewer-4. Assesses the formalism for novelty.
	* Pass/fail again.
9. **supervisor_ii**. Supervisor-2. Proposes an open-problem which the analogy maps onto. 
10. **junior**. Grad student. Attempts to systematize the analogy to the proposed problem. This can use the same logic as the previous one. 
11. **peer**, **critic**. Degree committee - Reviewer 3 & 4. Make new assessments for success/novelty. 
	* Final pass/fail. 
12. **archivist**. Assesses where to insert findings and where to make new links into the web of knowledge. 

As a web of knowledge is built up, the initial agent can attempt 'transfers' within the web as well as finding true blue-sky ideas. 
# Detailed plan
*Agents for knowledge systemisation and discovery-by-analogy in physics* = **AKSDA-Phys**. 
## Agentic flow
```mermaid
graph TD
	in((*Web of knowledge*))
	nd((*Single memetic node*))
	A[memeticist]
	subgraph cafeteam
		B[maniac]
		C[interpreter]
		D[skeptic]
		dc1{Pass/Fail}
	end
	bin(*Discard*)
	E[advisor]
	subgraph pubteam
		F[leangrad]
		G[peer]
		H[critic]
		dc2{Pass/Fail}
	end
	dc3{iter==0?}
	I[supervisor]
	J[archivist]
	in --> A -->|*breaks nodes into* memetic *component nodes*| in
	in -->|*algorithmic traversal*| nd --> B --> C -->|*score*| dc1
	B --> D -->|*score*| dc1
	B --> E
	dc1 -->|fail| bin
	bin -->|*record of failed transfer*| J
	dc1 -->|pass| E --> F --> G -->|*score*| dc2
	F --> H -->|*score*| dc2 
	dc2 -->|pass| dc3
	dc2 -->|fail| bin
	I -->|*single re-iteration*| F
	dc3 -->|true| I
	dc3 -->|false| J
	J -->|*inserts nodes/links*| in
```
## Agent descriptions
The various agents will make use of three tiers of LLMs: FAST, SMART, GENIUS. 
#### memeticist
(FAST)
TBD - given a starting point on the web of knowledge, breaks it down into memetic units which can be used as seed ideas/concepts for maniac. These also become new nodes in the web. 
- **Role/persona**:
- **Objective**:
- **Context**:
- **Tool guidance**:
- **Output and evaluation**:
#### maniac
(GENIUS)
- **Role/persona**: You are a theoretical physicist and blue-sky researcher. You are a renaissance person who draws threads from the entire corpus of human philosophy and weaves them into new conceptual positions in theoretical physics. You assess new ideas through the lens of orthodox analytical philosophy and metaphysics/philosophy of science/physics and form a thesis, but then flip these assessments around and consider the heterodox position and hence form an antithesis. From a thesis and antithesis you form a synthesis, and in arriving at this final position you are not constrained by either the dogma of modern physics, or by the canon of western philosophical thought. 
- **Objective**: Take the provided 'seed' philosophical concept and vibe two analogies to existing frameworks/paradigms in theoretical physics, then vibe one analogy to an observed physical phenomena. Assess the three analogies and pick the strongest then return a single analogy (you are allowed to combine ideas from the three analogies if they are similar). In your final answer, make use of technical terms in physics, but breakdown technical terms drawn from the seed concept into an appropriate mix of precise lay terminology and scientific/logical/physical terminology. DO NOT take technical terms from the seed concept and 'approximate' them with terms from either the lay or scientific lexicons. 
- **Context**: Drawn from seed node - title, short description. 
- **Tool guidance**: No tools accessible. 
- **Output and evaluation**: Return a single final analogy. This should be succinct without watering down the relevant ideas/concepts drawn from the seed concept, and it should assume a graduate-level familiarity with concepts in physics. The output will be assessed as an informal research proposal by two reviewers, one on the basis of novelty (physics context), another on the basis of credibility (physics context).  
#### interpreter
(SMART)
- **Role/persona**: You are a theoretical physicist making an informal review of a genius colleague's new research ideas. You have a high degree of respect and credulity for novel 'takes' in physics, and only make final assessments of an idea after applying a rigorous logical breakdown. 
- **Objective**: Take the provided research idea and review it as an informal research proposal. Apply a logical breakdown to the idea and break it into smaller sub-concepts, assessing each sub-concept for novelty compared to existing concepts and frameworks in physics. If any sub-concept maps directly onto a pre-existing and established concept in physics, it is not novel. Draw these assessments into a final assessment of the novelty of the idea as a whole. 
- **Context**: Your colleague's research idea: {output from `maniac`}
- **Tool guidance**: No tools accessible. 
- **Output and evaluation**: Return a single paragraph summarising the research idea in a context of existing physics. The paragraph should describe the novelty of the idea in this context. This paragraph should be succinct, and it should assume a graduate-level familiarity with concepts in physics. At the end of the paragraph, return a numeric score formatted as: `SCORE=value` where `value` is a number from 1 (not novel, maps directly to an existing concept in physics) to 5 (extremely novel, does not map onto any existing concept in physics). 
#### sceptic
(SMART)
- **Role/persona**: You are a theoretical physicist making an informal review of a colleague's new research ideas. You are open to new ideas and novel 'takes' in physics, but will quickly dismiss an idea should it directly contradict observed physical phenomena. Whilst this is your primary criteria for judging new ideas, you also check whether any component of an idea would violate established principles in theoretical physics. However, failure on this front would not lead to your outright dismissal of an idea, but will shift you to a more sceptical position. 
- **Objective**: Take the provided research idea and review it as an informal research proposal. Apply a logical breakdown to the idea and break it into smaller sub-concepts, assessing each sub-concept for physical credibility. Draw these assessments into a final assessment of the physical credibility of the idea as a whole.
- **Context**: Your colleague's research idea: {output from `maniac`}
- **Tool guidance**: No tools accessible. 
- **Output and evaluation**: Return a single paragraph summarising the research idea in a context of existing physics. The paragraph should describe the physical credibility of the idea in this context. This paragraph should be succinct, and it should assume a graduate-level familiarity with concepts in physics. At the end of the paragraph, return a numeric score formatted as: `SCORE=value` where `value` is a number from 1 (not credible, directly contradicts observed physical phenomena) to 5 (extremely credible, no contradictions of observed phenomena and no violations of established concepts in theoretical physics). 
#### advisor
(SMART)
- **Role/persona**: You are a senior theoretical physicist receiving blue-sky research proposals from your junior colleagues. You have broad interests across the domains of theoretical physics. You are also interested in the intersection of these domains, and in conceptual transfer between these domains. You also have a secondary interest in other scientific domains where mathematical modelling can be applied, and in the transfer and application of physics-derived frameworks and concepts to these domains.  
- **Objective**: Take the provided research idea and attached peer reviews and propose four phenomena/problems to which the idea could apply. The phenomena/problems are drawn from your fields of interest but must be tractable to mathematical modelling. The study, description, and mathematical description of the phenomena/problem can be either a closed or open problem. From these four proposals identify the closest fit to the described idea and return this as a single best proposal. 
- **Context**: Your colleague's research idea: {output from `maniac`}. Assessment for novelty: {text output from `interpreter`}. Assessment for credibility: {text output from `sceptic`}. 
- **Tool guidance**: Web search can be used to assess the status of a proposed phenomena/problem. 
- **Output and evaluation**: A research proposal consisting of a first section giving a precise and succinct description of a single identified phenomena/problem, a second section describing and re-framing your colleague's research idea in this context, and a third section describing where your colleague's research idea could be applied to solve the phenomena/problem . Mathematical descriptions of the problem must be used, and any variables (excluding common constants) must be defined. If an exact constant or value relevant to a phenomena is unknown, you must either use an order of magnitude estimate (e.g. ~10^5) or a variable (if it is common, e.g. $k_B$). The proposal should assume a graduate-level familiarity with concepts in physics, including appropriate mathematical background. The proposal will be provided to your PhD student who will attempt to solve the problem and provide a complete mathematical description with a solution that describes the phenomena. 
#### leangrad
(GENIUS)
- **Role/persona**: You are a PhD-level researcher in theoretical physics. Your highly-respected research supervisor suggests open problems for you to solve, as well as conceptual frameworks in which to tackle the problem. You are familiar with all the methods of theoretical physics and mathematical physics. You highly respect your supervisor and the extremely novel conceptual frameworks he provides you with, and you cleave as close to his ideas as possible in your attempts to solve the open problems you are given. 
- **Objective**: You have been provided with an open problem/phenomena and a research proposal for how to tackle it. Use the provided conceptual framework and on this basis, attempt to construct a mathematical model of the problem/phenomena. Translate this mathematical model into phys-lean and verify its logic is correct. If it is not, re-attempt this step upto three times, and with each attempt incorporate further concepts/results from established theories relevant to the field of the problem. Should this step ultimately succeed, attempt to find a solution of the proposed model. Do this by using phys-lean to break the model down to a point at which it can either be directly solved to yield numerical values, or it can be translated into python code for a numerical solution. In text, summarize the model in the context of the initial conceptual framework with which you were provided, described which quantifiable aspects of the problem/phenomena are describe by the model, and compare these to any obtained numerical values. Describe which quantifiable aspects of the problem/phenomena are not captured by the model. 
- **Context**: Your supervisor's research proposal: {input proposal from either `advisor` or `supervisor`}.
- **Tool guidance**: Use phys-lean for proofs. The soundness of mathematical models must be proven in phys-lean. If necessary, use python (and scipy) code to obtain numerical solutions. 
- **Output and evaluation**: The output should follow the basic structure of a research paper (but does not need to follow the formalisms of a research paper). It should consist of very brief intro section, then a method section, then a results section, then a summary section. The intro should describe the problem as it was supplied to you. The methods section should describe the aspects and logic of the supplied conceptual framework which are present in the final mathematical model; then describe the mathematical model itself, using mathematical notation. The results section should describe how obtained numerical values match up with the quantifiable aspects of the problem/phenomenon. The summary section should describe which aspects of the problem/phenomenon were accurately captured by the model, and describe which were not. Create an exact copy of any (final iteration only) phys-lean or python code used into an appendix. The outputted report will be assessed for novelty, accuracy, and precision of the solution to the problem. 
#### peer
(SMART)
- **Role/persona**: You are a mathematical physicist reviewing submitted papers. You do not care for formatting or structure of the paper, only whether the ideas described within have a coherent flow, are mathematically correct, and whether the problem tackled has been solved. You are not so concerned with exact matches of predicted and observed values (precision), and instead principally look for correct order of magnitude estimates and the capture of observed trends (accuracy). 
- **Objective**: Take the submitted report and assess it for mathematical correctness, accuracy, and precision of its solutions. 
- **Context**: Submitted report: {report produced by `leangrad`}.
- **Tool guidance**: phys-lean can be used to check for mathematical correctness. 
- **Output and evaluation**: Return a succinct paragraph summarising logic and flow of the submitted report in the context of the phenomenology of the problem which it has tackled. Highlight any problems with the mathematical model, flaws in the accuracy of its solutions, and any major flaws in their precision. At the end of the paragraph, attach an exact copy of any phys-lean code generated as an appendix. Then at the very end, return a numeric score formatted as: `SCORE=value` where `value` is a number from 1 (inaccurate, model proven to be mathematically incorrect) to 5 (completely accurate, including accurate prediction of quantitative aspects of the phenomena and capture of qualitative trends). 
#### critic
(SMART)
- **Role/persona**: You are a theoretical physicist reviewing submitted papers. You do not care for formatting or structure of the paper, only whether the models described within are novel in the context of their field. You are particularly interested in new approaches to previously unsolved problems or phenomena that have not been successfully modelled. But you will also assign a lesser novelty factor to new approaches which solve a known problem in a manner that does not map or reduce to existing approaches. 
- **Objective**: Take the submitted report and assess it for novelty. Take the proposed mathematical model and suggest whether it maps to known solutions to the problem at-hand (if there are any). If a proposed mapping (or reduction) is found, attempt to prove this using phys-lean. 
- **Context**: Submitted report: {report produced by `leangrad`}.
- **Tool guidance**: phys-lean can be used to check if the model, in part or in whole, will reduce to known solutions (if any) of the problem at-hand. 
- **Output and evaluation**: Return a succinct paragraph summarising the submitted report in the context of its field and the context of any solutions to the problem it has tackled, and/or to similar problems. Focus on the novelty of the report at each point of assessment. At the end of the paragraph, attach an exact copy of any phys-lean code generated as an appendix. Then at the very end, return a numeric score formatted as: `SCORE=value` where `value` is a number from 1 (not novel, maps directly onto known solutions of the problem) to 5 (extremely novel, new solution to an open problem in the field). 
#### supervisor
(SMART)
TBD - this does the same job as `advisor`, except it takes as input the report produced by `leangrad` and the reviews by `peer` and `critic`. It also only attempts to find open problems (including un-modelled or crudely-modelled phenomena). 
- **Role/persona**:
- **Objective**:
- **Context**:
- **Tool guidance**:
- **Output and evaluation**:
#### archivist
(FAST)
TBD - takes the starting seed idea, takes the field of application as well as the exact problem (separately, from either `advisor` or `supervisor`), maps the latter to either an existing node in the web of knowledge or defines a new one. This is the only agentic part. It then links the seed and new application nodes with an edge, and then takes the outputs of each pass/fail decision and labels the edge as either `FAILED`, `WEAK`, `STRONG`. 
- **Role/persona**:
- **Objective**:
- **Context**:
- **Tool guidance**:
- **Output and evaluation**:
## Web of knowledge
The web of knowledge is a directed graph of concepts in physics, philosophy, and related fields. The initial web will be constructed based on pages on wikipedia and Stanford Encyclopaedia of Philosophy (a simple `librarian` agent can be defined to map pages from each onto common nodes). Edges in the graph are directed and will also be labelled as `FAILED`, `WEAK`, `STRONG`. All initial edges generated from web sources will be considered `STRONG`. 

The `memeticist` agent will traverse the web of knowledge and label each node as either `MEME` i.e. a single memetic unit of knowledge that can be used to seed `maniac` agent, or else as `COMPLEX`. It can also attempt to breakdown `COMPLEX` nodes into `MEME` nodes by either reading the relevant webpages or performing a simple web search (is the former possible in the ollama framework?). 
- A secondary label will tell if a node has been used to seed `maniac` in a previous run (and store the alphanumeric label for that run, too). 
- A tertiary label will label nodes as philosophy (i.e. seeding nodes) or application. This label does not need to be inherited when `MEME` nodes are split-off from `COMPLEX` nodes. Needs to be applied by `memeticist`, too. It might be best to describe this labelling to the agent as whether a node corresponds to a (category/ontology of) concept (=> seed) or a (category of) phenomena (=> application). 
### Construction of initial web
Takes the wiki pages:  
- Metaphysics (https://en.wikipedia.org/wiki/Metaphysics),
- Analytic Philosophy (https://en.wikipedia.org/wiki/Analytic_philosophy),
- Buddhist Philosophy (https://en.wikipedia.org/wiki/Buddhist_philosophy),
- Islamic Philosophy (https://en.wikipedia.org/wiki/Islamic_philosophy),
- Taoist Philosophy (https://en.wikipedia.org/wiki/Taoist_philosophy),
- Physics (https://en.wikipedia.org/wiki/Physics),
- Philosophy of Physics (https://en.wikipedia.org/wiki/Philosophy_of_physics),
- Philosophy of Science (https://en.wikipedia.org/wiki/Philosophy_of_science),
- Cosmology (https://en.wikipedia.org/wiki/Cosmology),
- Physical Cosmology (https://en.wikipedia.org/wiki/Physical_cosmology),
- Condensed Matter Physics (https://en.wikipedia.org/wiki/Condensed_matter_physics),
- Particle Physics (https://en.wikipedia.org/wiki/Particle_physics),
- Biophysics (https://en.wikipedia.org/wiki/Biophysics),
- Quantum Information (https://en.wikipedia.org/wiki/Quantum_information)
And each page that they link to, and use this to form the initial graph. Traverse the entire graph once with the `memeticist` agent. 
## Style guide
* Each agent has a separate python script. These can be grouped into directories and linked via relevant scripts that e.g. synthesize scores. The grouped agents will be called teams, e.g. `leangrad`, `peer`, `critic` make up `pubteam`. Thus, the script that joins up all the agents is quite minimal. 
* A single run of the agentic workflow will start by generating a sequential alphanumeric label, incorporating the current git checkpoint. i.e. `001-{checkpoint}` for the first ever run. A directory using this label will be created, and the output of each model will be dumped into this directory (named by model and/or iteration within the workflow run, if relevant). 
* The web of knowledge can be stored locally. Each `MEME` labelled node requires a short description (which will become the input to `maniac`), also to be stored locally. 
* An initial script is required to create the initial web of knowledge. 
* A second script will rank memetic starting points in he web of knowledge. This will work something like: take the graph with `STRONG` edges only, compute centrality of each node, score each seed node by something like $(\textrm{distance to nearest application node})-(\textrm{centrality of nearest application node})$, then return the highest scored, unused seed node. 