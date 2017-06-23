
Alfred Fixum
============

Fix Alfred 3 Python workflows affected by bugs in [Alfred-Workflow][aw], in particular the [the Sierra background process bug][bug].

Fixum analyses your installed workflows to see if any use an old version of the Alfred-Workflow library. If they do, it can update them with a newer, working version.


Installation
------------

Download from [GitHub releases][releases].


Usage
-----

Before you use this workflow, make a backup of your workflows directory. To get to it, right-click on a workflow in Alfred Preferences, choose **Open in Finder**, then navigate to the parent `workflows` directory. Drag a copy to your Desktop or run **Compress "workflows"** on it from the context menu.

*__Don't__* immediately run **Fix Workflows**, but rather be sure to **View Log File** and use **Dry Run** a few times to check this workflow isn't going to overwrite something it shouldn't.

**NOTE:** Fixum only looks in real directories and ignores symlinks.

If there are any workflows you don't want updating, use **Edit Blacklist** and add their bundle IDs to that file before you run **Fix Workflows**.

 Opening Alfred's debugger will turn on debugging mode, and the log will contain more information.

If everything looks good, run **Fix Workflows**.


### Alfred commands ###

- `fixum` — Show available actions
    - **A newer version of Fixum is available** — Shown if an update
      for Fixum is available.
    - **Dry Run** — Analyse installed workflows, but don't change anything
    - **View Log File** — See what the workflow would change/has changed
    - **Edit Blacklist** — Change the list of bundle IDs that should not be updated (e.g. your own workflows)
    - **Fix Workflows** — Replace any buggy versions of Alfred-Workflow with a newer, working one


If anything goes wrong
----------------------

To restore a workflow's original Alfred-Workflow library if the fix actually broke it, open the workflow in Finder (right-click on it in Alfred Preferences and choose **Open in Finder**). Find the `workflow` and `workflow.old` directories, trash `workflow` and rename `workflow.old` to `workflow`. That puts back the original version.


Getting help
------------

Post [a GitHub issue][issues], or visit the [thread for this workflow][forum-fixum] or the [one for Alfred-Workflow][forum-aw] on [the Alfred forum](https://www.alfredforum.com).


[mit]: ./src/LICENCE.txt
[aw]: https://github.com/deanishe/alfred-workflow/
[bug]: https://github.com/deanishe/alfred-workflow/issues/111
[forum-aw]: https://www.alfredforum.com/topic/4031-workflow-library-for-python/
[forum-fixum]: https://www.alfredforum.com/topic/10193-python-fix-how-to-fix-python-workflows-hanging-alfred-on-sierra/
[issues]: https://github.com/deanishe/alfred-fixum/issues/
[releases]: https://github.com/deanishe/alfred-fixum/releases/latest
