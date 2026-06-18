import { setupServer } from 'msw/node'
import { authHandlers } from './handlers/auth.handlers'
import { adminUsersHandlers } from './handlers/adminUsers.handlers'

export const server = setupServer(...authHandlers, ...adminUsersHandlers)
