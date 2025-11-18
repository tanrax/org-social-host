# Org Social host

This is a system that allows you to host your `social.org` files online. It automatically provides you with a nickname and a system to update or share your file with other users.

It is useful for:

- Taking your first steps in the community
- Updating your public file online
- Synchronizing multiple devices or clients with the same `social.org`

## Very Important Notice

If you don't update your `social.org` at least **once a month**, you will lose the domain and the nickname will be released.

## Usage

### Quickstart (Registration and client configuration)

Go to https://host.org-social.org/signup and choose a nickname.

Or using the terminal:

```sh
curl -X POST https://host.org-social.org/signup \
  -H "Content-Type: application/json" \
  -d '{"nick": "my-nick"}'
```

Replace `my-nick` with your desired nickname.

If the nickname is available, you will receive 2 elements that you must keep very safe:

- `vfile`: a path that represents your `social.org` file in a unique and virtual way. You should not share it with anyone. The format is usually like this: `https://host.org-social.org/vfile?token=123456789&ts=1700000000&sig=abc123`.
- `public-url`: the public URL where your `social.org` file will be hosted. You can share this URL with anyone you want. The format is usually like this: `https://host.org-social.org/my-nick/social.org`.

If you use the `org-social.el` client, you should configure it as follows:

```elisp
(setq org-social-file "YOUR_VFILE_HERE")  ;; Your vfile here
(setq org-social-my-public-url "YOUR_PUBLIC_URL_HERE")  ;; Your public-url here
(setq org-social-relay "https://relay.org-social.org/")  ;; Relay server
```

Next, edit your `social.org` file with `M-x org-social-open-file` and save it with `C-x C-s` to upload it to the server.

Once you have included some followers, you can open the timeline with `M-x org-social-timeline`.

### Update your `social.org` file

The client will take care of updating your `social.org` file on the server every time you save it.

If you want to do it manually, you can use the following command:

```sh
curl -X POST https://host.org-social.org/upload \
    -F "vfile=YOUR_VFILE_HERE" \
    -F "file=@/path/to/your/social.org"
```

### Delete your `social.org` file

If you wish to delete your `social.org` file from the server, you can do so with the following command:

```sh
curl -X POST https://host.org-social.org/delete \
    -H "Content-Type: application/json" \
    -d '{"vfile": "YOUR_VFILE_HERE"}'
```

This is a non-reversible action!

Alternatively, wait for 1 month without updating it, in which case it will be automatically deleted.

### Custom redirection

You may want to move your file from `host.org-social.org` to another domain, hosting, or server; but you don't want to lose your followers (who are pointing to a host domain). In that case, you have a custom redirection feature for migration that is permanent (HTTP 301).

To do this, use the following command:

```sh
curl -X POST https://host.org-social.org/redirect \
    -H "Content-Type: application/json" \
    -d '{"vfile": "YOUR_VFILE_HERE", "new-url": "https://my-new-domain.org/social.org"}'
```

You will no longer be able to update your file. Your `public-url` will redirect to the new URL you specified. You can do this action as many times as you want.

Although your followers won't notice the change, we recommend notifying them of the migration so they can update their `social.org` with the new URL.

To remove the redirection and return to the previous state where you could upload a file, execute the following command:

```sh
curl -X POST https://host.org-social.org/remove-redirect \
    -H "Content-Type: application/json" \
    -d '{"vfile": "YOUR_VFILE_HERE"}'
```

## Support

Except for serious errors, this service is free and does not offer technical support.

Open an issue in this repository if:

- An endpoint is not working as it should.
- The service is down.
- There is a serious security error.
- You have a suggestion for improvement.
- You want to contribute to the project.

Technical support requests for individual user problems will not be addressed, nor will accidentally deleted files or files lost due to inactivity be recovered. It will also not be possible to reserve nicknames or domains, recover lost `vfile`s, or transfer nicknames between users.
