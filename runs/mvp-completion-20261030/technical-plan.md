# Technical plan: shared shell and two pilots

Saved/condensed by orchestrator from actual /root/mvp_architect response. Architect read role/skills/specs/catalog plus original source; reported checked hashes match. It reviewed the shared hosting contract. No auto-discovery claim.

## Shared architecture

One local process owns two endpoints: loopback Flask/Werkzeug web thread (8080) and Bokeh server IOLoop (5006). Each app invokes build_document(doc) per session and creates ALL widgets/sources/ranges/closures locally. SIGINT/SIGTERM stop the loop, close Bokeh, shut down/join Flask thread and release ports. Check readiness of BOTH endpoints and cleanup after partial failure. This adapts SINDy run.sh without fixed sleeps or reloaders. Local development only.

Module package: __init__.py, engine.py, ui.py exporting build_document(doc), module.json containing title/subtitle/objectives/assumptions/questions, requirements.txt referencing shared lock. Root loader uses isolated package namespace and relative imports. Responsive controls/figures stretch_width, min_width around 280, vertically stacked plots. Shared Jinja/HTML shell renders content/assessment.

## Scientific APIs

Projectile trajectory(speed, angle, *, samples=201) returns time,x,y arrays and flight_time,range,max_height scalars. Validate finite speed[0,50], angle[0,90], integer samples>=2 (bounded). g=9.81. T=2*v*sin(theta)/g; R=v²*sin(2theta)/g; H=v²*sin²(theta)/(2g). Zero speed or horizontal launch gives finite zero-duration trajectory; vertical x/range exactly0. Clamp only endpoint roundoff. Named Bokeh models: speed, angle sliders; trajectory CDS {t,x,y}; metrics Div with units.

Regression generate_data(noise,n,seed) -> Dataset(x,y,standard_noise,train_idx,test_idx); fit_and_evaluate(dataset)->result(slope,intercept,predictions,residuals,train_mse,test_mse). Validate noise[0,5], integer n[20,300], seed bounded nonnegative. float64 x=linspace(0,10,n); y=2*x+1+noise*z. Construct seeded RNG, generate z then permutation in fixed order independent of noise; first floor(.75*n) training, rest test. Fit numpy.linalg.lstsq([x_train,ones], y_train), require rank2; validate finite aligned arrays and disjoint/exhaustive integer indices. No preprocessing. Residual=y-pred; MSE=mean(residual²).

Regression names: noise, sample_count sliders; seed integer input; generate button; observations CDS {x,y,prediction,residual,split,marker}; residuals CDS {x,residual,split,marker}; fit_line/true_line CDS {x,y} with two points; metrics Div committed equation/config/counts/MSE; status Div pending input edits. Train circles/test triangles plus colors and legend. Changes mark pending; Generate commits. True line fixed generating relationship, fitted line distinct; residual zero baseline.

## Verification

Use stdlib unittest (Architect suggested pytest but no need for additional test dependency). Independent PM oracle at20/30: T=20/9.81, R=200*sqrt(3)/9.81, H=50/9.81; verify trajectories, edges and invalid inputs. Independent LR centered-sums OLS and manual residual/MSE; alter only held-out y and require same fitted coefficients; zero-noise recovery tolerance1e-12; reproducibility/partition validation. Build two Documents and verify independent models/callback state, plus actual two-browser sessions. Browser controls and click actions must update actual server-backed sources; inspect desktop/narrow rendering. Root verifies clean dependency environment, launcher, ports, shared scaffold and docs. QA maps PM-01–08 and LR-01–10 to evidence; missing required checks stay visible.

Packages: NumPy for arrays/RNG/OLS; Flask shell; Bokeh Python interactions; no SciPy/sklearn for two coefficients. Synchronous calculations appropriate for <=201/10001 bounded trajectory points and<=300 regression rows; benchmark before claiming durations. No neural training.

## Reuse/adaptation

SINDy main.py per-session state -> all state in build_document; engine layer -> pure scientific APIs; flask_app.py/templates/index.html -> shared metadata-driven lesson shell; tabs/test_tab.py -> explicit held-out comparison and diagnostics; run.sh -> single owner of dual-service lifecycle with readiness checks; source layout -> responsive vertical plots. Three questions/feedback per learning spec, no irrelevant history/upload/training tabs.

Read evidence: AGENTS.md, architect role and three skills, current learning spec/brief/design/runtime/usage, catalog/case study and originals main.py,flask_app.py,run.sh,tabs/test_tab.py,templates/index.html. Automatic role selection/preloading, browser acceptance, dependency compatibility and performance unverified at design time. No learning-gain or productivity claim.
