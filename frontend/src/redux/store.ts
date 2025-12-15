import {configureStore} from '@reduxjs/toolkit'
import authReducer from './slices/authReducer'
import goalsReducer from './slices/goalsSlice'
import taskReducer from './slices/tasksSlice'

export const store= configureStore({
    /**
     * 1.We will use Redux to manage the global authentication state:
      the user object, loading status, and authentication status. as described in the authReducer
     */
    reducer:{
        auth:authReducer,
        goals:goalsReducer,
        tasks:taskReducer
    }})

//Define types for global state  and for dispatch
export type RootState=ReturnType<typeof store.getState>
export type AppDispatch=typeof store.dispatch