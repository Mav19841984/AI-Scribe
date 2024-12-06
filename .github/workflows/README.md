# Pushing and Building Release on GitHub Workflow

## Steps to Push and Build a Release

1. **Checkout the main branch:**

    ```sh
    git checkout main
    ```

2. **Pull the latest changes from the main branch:** 

    ```sh
    git pull origin main
    ```

3. **Tag the release:**

    ```sh
    git tag <tag-version>
    ```

    Example:

    ```sh
    git tag v0.0.1
    ```

4. **Push the changes and the tag to the remote repository:**

    ```sh
    git push origin <tag-version>
    ```

    Example:

    ```sh
    git push origin v0.0.1
    ```

## Tagging Conventions

- `vx.x.x` tags latest release.
- `vx.x.x.alpha` tags pre-release.
