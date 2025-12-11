import {configureStore} from '@reduxjs/toolkit'
import authReducer from './slices/authReducer'

export const store= configureStore({
    /**
     * 1.We will use Redux to manage the global authentication state:
      the user object, loading status, and authentication status. as described in the authReducer
     */
    reducer:{
        auth:authReducer,
    }})

//Define types for global state  and for dispatch
export type RootState=ReturnType<typeof store.getState>
export type AppDispatch=ReturnType<typeof store.dispatch>