# Backend Folder Guide

Use this file when starting backend work in a new conversation.

## Where New Files Should Go

- backend code: [backend](/C:/Users/Yang/Desktop/miro/backend)
- shared contracts and enums: [shared](/C:/Users/Yang/Desktop/miro/shared)
- API docs and contract drafts: [docs/api](/C:/Users/Yang/Desktop/miro/docs/api)
- product and flow references: [docs](/C:/Users/Yang/Desktop/miro/docs/README.md)

## Quick Routing

- New route/controller file -> `backend/app/api`
- New module implementation -> `backend/app/modules`
- New database model or repository -> `backend/app/db` or `backend/app/models`
- New migration -> `backend/migrations`
- New backend test -> `backend/tests`
- New shared enum -> `shared/enums`
- New shared payload contract -> `shared/contracts`
- New shared validation schema -> `shared/schemas`

## Do Not Mix

- frontend page/component files should stay under [src](/C:/Users/Yang/Desktop/miro/src)
- screenshots and QA outputs should stay under [artifacts](/C:/Users/Yang/Desktop/miro/artifacts)
- product and architecture notes should stay under [docs](/C:/Users/Yang/Desktop/miro/docs)
