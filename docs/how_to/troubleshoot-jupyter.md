# Troubleshoot Jupyter Launch Issues

This guide helps you resolve issues when Jupyter is stuck in the "Launching" state and won't load your notebooks.

## The Problem

When you try to open a Jupyter notebook in NOMAD Oasis, it may:

- Stay stuck on "Launching..." indefinitely
- Show a loading spinner that never completes
- Fail to open the notebook interface
- Time out without error messages

## Quick Solution

The most common cause is session authentication. Here's the fix:

### Step 1: Access the Authentication Page

Go to your NOMAD Oasis Jupyter authentication endpoint.

!!! info "URL Format"
    The URL is typically:
    ```
    https://your-nomad-oasis.domain/nomad-oasis/ui/api/v1/repo/users/me/jupyter
    ```
    
    Replace `your-nomad-oasis.domain` with your actual NOMAD Oasis server address.

Ask your NOMAD administrator or colleagues for the exact URL if you're unsure.

### Step 2: Sign In

1. On the authentication page, look for a **lock icon** in the top right corner

2. Click the lock icon to open the login prompt

3. **Sign in with your NOMAD credentials**:
   - Username: Your NOMAD username
   - Password: Your NOMAD password

### Step 3: Execute Authentication

1. After signing in, you'll see an "Execute" or "Try it out" button

2. In the field that appears, type:
   ```
   jupyter
   ```

3. Click **"Execute"**

This authenticates your Jupyter session with NOMAD's API.

### Step 4: Return to Your Notebook

1. Go back to the notebook you were trying to open

2. Refresh the page or try launching again

3. Jupyter should now load properly

## Alternative Solutions

If the quick fix doesn't work, try these:

### Solution 2: Clear Browser Cache

Stale session data can cause authentication issues.

1. **Clear your browser cache**:
   - Chrome/Edge: Ctrl+Shift+Delete (Windows) or Cmd+Shift+Delete (Mac)
   - Firefox: Ctrl+Shift+Delete (Windows) or Cmd+Shift+Delete (Mac)
   - Select "Cached images and files"
   - Choose "Last hour" or "Last 24 hours"

2. **Close and reopen your browser**

3. Log back into NOMAD Oasis

4. Try launching the notebook again

### Solution 3: Use Incognito/Private Mode

Browser extensions or saved state can interfere.

1. **Open an incognito/private window**:
   - Chrome: Ctrl+Shift+N (Windows) or Cmd+Shift+N (Mac)
   - Firefox: Ctrl+Shift+P (Windows) or Cmd+Shift+P (Mac)
   - Edge: Ctrl+Shift+N (Windows) or Cmd+Shift+N (Mac)

2. Navigate to NOMAD Oasis and log in

3. Try launching your notebook

If this works, the issue is browser-related (extensions, cache, cookies).

### Solution 4: Wait and Retry

Sometimes the server is temporarily busy.

1. **Wait 2-3 minutes** before retrying

2. Jupyter servers may need time to:
   - Allocate resources
   - Initialize the kernel
   - Load required packages

3. Refresh the page after waiting

### Solution 5: Check Server Status

The NOMAD Oasis server may be experiencing issues.

1. **Ask colleagues** if they can launch Jupyter successfully

2. **Check system status**:
   - Look for maintenance notifications
   - Contact your NOMAD administrator
   - Check group communication channels

3. If server-wide, wait for administrators to resolve

### Solution 6: Try a Different Notebook

The specific notebook file may be corrupted.

1. Try opening a **different notebook** in NOMAD

2. If others work, the issue is with that specific notebook

3. **Solutions for corrupted notebooks**:
   - Regenerate the notebook (if created from template)
   - Delete and recreate the Jupyter Analysis entry
   - Contact support to recover notebook content

### Solution 7: Restart Your Session

Force NOMAD to create a fresh session.

1. **Log out** of NOMAD Oasis completely

2. **Close all browser tabs** with NOMAD

3. Wait 1 minute

4. **Open a new browser window** and log in

5. Try launching Jupyter

## Prevention Tips

Avoid future Jupyter launch issues:

### Keep Sessions Active

- Don't leave notebooks idle for extended periods
- Jupyter sessions may timeout (typical: 1-4 hours)
- Save work frequently and relaunch when needed

### Use Compatible Browsers

NOMAD works best with:

- ✅ Chrome (recommended)
- ✅ Firefox
- ✅ Edge (Chromium-based)
- ⚠️ Safari (may have compatibility issues)
- ❌ Internet Explorer (not supported)

### Maintain Browser Updates

- Keep your browser updated to the latest version
- Outdated browsers may have authentication or rendering issues

### Save Notebooks Regularly

- Use Ctrl+S (or Cmd+S) frequently while working
- NOMAD autosaves, but manual saves ensure data integrity
- Prevents loss if you need to force-restart

## Understanding the Issue

### Why does this happen?

Jupyter in NOMAD runs as a separate service that requires:

1. **Authentication** - Verifyyou have permission to access computational resources
2. **Session management** - Track your active notebook sessions
3. **Resource allocation** - Assign CPU, memory, and storage

When any step fails, Jupyter can't launch.

### Common causes:

- **Expired authentication tokens** - Most common, fixed by re-authenticating
- **Server resource limits** - Too many concurrent users
- **Network issues** - Connection problems between browser and server
- **Browser state** - Stale cookies or cached credentials

## When to Contact Support

Contact your NOMAD administrator if:

- [x] You've tried all solutions above
- [x] No one in your group can launch Jupyter
- [x] The issue persists for > 24 hours
- [x] You see specific error messages (provide screenshots)
- [x] Jupyter works in incognito but not regular browser

**Information to provide:**

- Your NOMAD username
- Browser and version
- Operating system
- Steps you've already tried
- Screenshots of any error messages
- Approximate time when issue started

## Related Resources

- [Plot Combinatorial EDX Data](plot-combinatorial-edx.md) - Using Jupyter for visualization
- [Jupyter Analysis Reference](../reference/analysis.md) - Understanding Jupyter Analysis entries
- [Tutorial](../tutorial/tutorial.md) - Complete workflow including Jupyter

## Still Having Issues?

If none of these solutions work:

1. **Document the problem**:
   - Take screenshots
   - Note exact error messages
   - Record steps to reproduce

2. **Try workarounds**:
   - Download the notebook and run locally (if possible)
   - Ask a colleague to open it and export results
   - Use alternative analysis methods temporarily

3. **Report to support** with all documentation

Most Jupyter launch issues resolve quickly with re-authentication. If problems persist, they usually indicate server or network issues requiring administrator intervention.
