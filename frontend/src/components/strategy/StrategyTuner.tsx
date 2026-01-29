// src/components/strategy/StrategyTuner.tsx
/**
 * Strategy Tuner Component
 * ========================
 * 
 * A high-quality "Values Dashboard" that allows users to configure
 * their strategic weights using an intuitive slider interface.
 * 
 * Features:
 * ---------
 * - Four sliders (Work, Study, Health, Relationships)
 * - Real-time sum validation
 * - Visual budget indicator
 * - Auto-normalization option
 * - Accessible (ARIA-compliant) controls
 * 
 * Normalization Math:
 * -------------------
 * All weights must sum to exactly 1.0 (100%).
 * 
 * Two modes are supported:
 * 
 * 1. **Manual Mode** (default):
 *    User adjusts each slider independently. The UI shows the
 *    "remaining budget" and disables Save if sum ≠ 1.0.
 * 
 * 2. **Auto-Normalize Mode** (optional):
 *    When one slider is moved, the others proportionally adjust
 *    to maintain sum = 1.0.
 * 
 *    Formula for proportional adjustment:
 *    For a change from oldValue to newValue on slider X:
 *    
 *    remainingBudget = 1.0 - newValue
 *    sumOfOthers = sum of other sliders' current values
 *    
 *    If sumOfOthers > 0:
 *      For each other slider Y:
 *        Y.newValue = Y.oldValue × (remainingBudget / sumOfOthers)
 *    Else:
 *      Distribute remainingBudget equally among others
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
    fetchWeights,
    saveWeights,
    resetWeights,
    setDraftWeight,
    setAllDraftWeights,
    discardDraftChanges,
    selectDraftWeights,
    selectDraftSum,
    selectIsDraftValid,
    selectHasUnsavedChanges,
    selectWeightsLoading,
    selectWeightsSaving,
    selectWeightsError,
    selectNeedsReprioritization,
    acknowledgeReprioritization,
} from '@/redux/slices/weightsSlice';
import { getPrioritizedTasks } from '@/redux/slices/tasksSlice';
import {
    WeightDomain,
    WEIGHT_DOMAINS,
    DOMAIN_CONFIG,
    weightToPercent,
    formatWeightPercent,
    getRemainingBudget,
    StrategicWeights,
} from '@/types/weights';
import { AppDispatch } from '@/redux/store';


// ---------------------------------------------------------------------------
// COMPONENT PROPS
// ---------------------------------------------------------------------------

interface StrategyTunerProps {
    /** Enable auto-normalization mode */
    autoNormalize?: boolean;
    
    /** Callback when weights are saved successfully */
    onSaveSuccess?: () => void;
    
    /** Compact mode for sidebar display */
    compact?: boolean;
}


// ---------------------------------------------------------------------------
// MAIN COMPONENT
// ---------------------------------------------------------------------------

const StrategyTuner: React.FC<StrategyTunerProps> = ({
    autoNormalize = false,
    onSaveSuccess,
    compact = false,
}) => {
    const dispatch = useDispatch<AppDispatch>();
    
    // Redux state
    const draftWeights = useSelector(selectDraftWeights);
    const draftSum = useSelector(selectDraftSum);
    const isValid = useSelector(selectIsDraftValid);
    const hasChanges = useSelector(selectHasUnsavedChanges);
    const loading = useSelector(selectWeightsLoading);
    const saving = useSelector(selectWeightsSaving);
    const error = useSelector(selectWeightsError);
    const needsReprioritization = useSelector(selectNeedsReprioritization);
    
    // Local state for auto-normalize toggle
    const [isAutoNormalize, setIsAutoNormalize] = useState(autoNormalize);
    
    // Fetch weights on mount
    useEffect(() => {
        dispatch(fetchWeights());
    }, [dispatch]);
    
    // Handle re-prioritization notification
    useEffect(() => {
        if (needsReprioritization) {
            // Refresh tasks with new weights
            dispatch(getPrioritizedTasks());
            dispatch(acknowledgeReprioritization());
            onSaveSuccess?.();
        }
    }, [needsReprioritization, dispatch, onSaveSuccess]);
    
    /**
     * Handle slider value change.
     * 
     * In auto-normalize mode, adjusts other sliders proportionally.
     * In manual mode, just updates the single value.
     */
    const handleSliderChange = useCallback(
        (domain: WeightDomain, newValue: number) => {
            // Round to avoid floating-point display issues
            const roundedValue = Math.round(newValue * 100) / 100;
            
            if (isAutoNormalize) {
                // Calculate proportional adjustment for other sliders
                const remaining = 1.0 - roundedValue;
                
                // Get current values of other domains
                const otherDomains = WEIGHT_DOMAINS.filter(d => d !== domain);
                const currentOthersSum = otherDomains.reduce(
                    (sum, d) => sum + (draftWeights[d] ?? 0.25),
                    0
                );
                
                // Calculate new values for other domains
                const newWeights: Partial<StrategicWeights> = {
                    [domain]: roundedValue,
                };
                
                if (currentOthersSum > 0.001) {
                    // Proportional distribution
                    otherDomains.forEach(d => {
                        const currentValue = draftWeights[d] ?? 0.25;
                        const proportion = currentValue / currentOthersSum;
                        newWeights[d] = Math.round(remaining * proportion * 100) / 100;
                    });
                } else {
                    // Equal distribution among others
                    const equalShare = remaining / otherDomains.length;
                    otherDomains.forEach(d => {
                        newWeights[d] = Math.round(equalShare * 100) / 100;
                    });
                }
                
                // Adjust for rounding errors to ensure exact 1.0 sum
                const newSum = Object.values(newWeights).reduce((a, b) => a + (b ?? 0), 0);
                if (Math.abs(newSum - 1.0) > 0.001) {
                    // Add/subtract difference from the changed slider
                    newWeights[domain] = roundedValue + (1.0 - newSum);
                }
                
                dispatch(setAllDraftWeights(newWeights));
            } else {
                // Manual mode - just update single value
                dispatch(setDraftWeight({ domain, value: roundedValue }));
            }
        },
        [dispatch, draftWeights, isAutoNormalize]
    );
    
    /**
     * Handle save button click.
     */
    const handleSave = useCallback(() => {
        if (!isValid) return;
        
        dispatch(saveWeights({
            work_bills: draftWeights.work_bills,
            study: draftWeights.study,
            health: draftWeights.health,
            relationships: draftWeights.relationships,
        }));
    }, [dispatch, draftWeights, isValid]);
    
    /**
     * Handle reset to defaults.
     */
    const handleReset = useCallback(() => {
        dispatch(resetWeights());
    }, [dispatch]);
    
    /**
     * Handle discard changes.
     */
    const handleDiscard = useCallback(() => {
        dispatch(discardDraftChanges());
    }, [dispatch]);
    
    // Calculate remaining budget for display
    const remainingBudget = useMemo(() => getRemainingBudget(draftSum), [draftSum]);
    const remainingPercent = weightToPercent(Math.abs(remainingBudget));
    const isOverBudget = draftSum > 1.001;
    const isUnderBudget = draftSum < 0.999;
    
    // Loading state
    if (loading) {
        return (
            <div style={containerStyle}>
                <div style={loadingStyle}>Loading your strategic profile...</div>
            </div>
        );
    }
    
    return (
        <div style={{ ...containerStyle, ...(compact && compactContainerStyle) }}>
            {/* Header */}
            <header style={headerStyle}>
                <h2 style={titleStyle}>Strategic Values</h2>
                <p style={subtitleStyle}>
                    Define what matters most to you. These weights determine how tasks are prioritized.
                </p>
            </header>
            
            {/* Budget Indicator */}
            <BudgetIndicator
                sum={draftSum}
                isValid={isValid}
                isOverBudget={isOverBudget}
                isUnderBudget={isUnderBudget}
                remaining={remainingBudget}
            />
            
            {/* Auto-Normalize Toggle */}
            <div style={toggleContainerStyle}>
                <label style={toggleLabelStyle}>
                    <input
                        type="checkbox"
                        checked={isAutoNormalize}
                        onChange={(e) => setIsAutoNormalize(e.target.checked)}
                        style={checkboxStyle}
                    />
                    <span>Auto-balance sliders</span>
                </label>
                <small style={toggleHintStyle}>
                    {isAutoNormalize
                        ? 'Moving one slider adjusts others to maintain 100%'
                        : 'Adjust each slider independently'}
                </small>
            </div>
            
            {/* Sliders */}
            <div style={slidersContainerStyle}>
                {WEIGHT_DOMAINS.map(domain => (
                    <WeightSlider
                        key={domain}
                        domain={domain}
                        value={draftWeights[domain] ?? 0.25}
                        onChange={(value) => handleSliderChange(domain, value)}
                        compact={compact}
                    />
                ))}
            </div>
            
            {/* Error Message */}
            {error && (
                <div style={errorStyle}>
                    <span style={errorIconStyle}>⚠️</span>
                    {error}
                </div>
            )}
            
            {/* Action Buttons */}
            <div style={actionsStyle}>
                <button
                    onClick={handleSave}
                    disabled={!isValid || !hasChanges || saving}
                    style={{
                        ...buttonStyle,
                        ...primaryButtonStyle,
                        ...(!isValid || !hasChanges || saving ? disabledButtonStyle : {}),
                    }}
                    aria-label="Save weights"
                >
                    {saving ? 'Saving...' : 'Save Changes'}
                </button>
                
                <button
                    onClick={handleDiscard}
                    disabled={!hasChanges || saving}
                    style={{
                        ...buttonStyle,
                        ...secondaryButtonStyle,
                        ...(!hasChanges || saving ? disabledButtonStyle : {}),
                    }}
                    aria-label="Discard changes"
                >
                    Discard
                </button>
                
                <button
                    onClick={handleReset}
                    disabled={saving}
                    style={{
                        ...buttonStyle,
                        ...tertiaryButtonStyle,
                        ...(saving ? disabledButtonStyle : {}),
                    }}
                    aria-label="Reset to defaults"
                >
                    Reset to Default
                </button>
            </div>
            
            {/* Validation Hint */}
            {!isValid && (
                <p style={validationHintStyle}>
                    {isOverBudget
                        ? `Reduce allocations by ${remainingPercent}% to save`
                        : `Allocate the remaining ${remainingPercent}% to save`}
                </p>
            )}
        </div>
    );
};


// ---------------------------------------------------------------------------
// SUB-COMPONENTS
// ---------------------------------------------------------------------------

interface BudgetIndicatorProps {
    sum: number;
    isValid: boolean;
    isOverBudget: boolean;
    isUnderBudget: boolean;
    remaining: number;
}

const BudgetIndicator: React.FC<BudgetIndicatorProps> = ({
    sum,
    isValid,
    isOverBudget,
    isUnderBudget,
    remaining,
}) => {
    const percent = weightToPercent(sum);
    
    // Determine color based on validity
    const barColor = isValid
        ? '#10b981'  // Green
        : isOverBudget
        ? '#ef4444'  // Red
        : '#f59e0b'; // Amber
    
    return (
        <div style={budgetContainerStyle}>
            <div style={budgetHeaderStyle}>
                <span style={budgetLabelStyle}>Budget Allocation</span>
                <span style={{ ...budgetValueStyle, color: barColor }}>
                    {percent}%
                </span>
            </div>
            
            {/* Progress Bar */}
            <div style={progressBarContainerStyle}>
                <div
                    style={{
                        ...progressBarFillStyle,
                        width: `${Math.min(percent, 100)}%`,
                        backgroundColor: barColor,
                    }}
                />
                {/* 100% marker */}
                <div style={progressMarkerStyle} />
            </div>
            
            {/* Status Message */}
            <div style={budgetStatusStyle}>
                {isValid && (
                    <span style={{ color: '#10b981' }}>✓ Perfect balance</span>
                )}
                {isOverBudget && (
                    <span style={{ color: '#ef4444' }}>
                        Over by {weightToPercent(Math.abs(remaining))}%
                    </span>
                )}
                {isUnderBudget && (
                    <span style={{ color: '#f59e0b' }}>
                        {weightToPercent(remaining)}% remaining
                    </span>
                )}
            </div>
        </div>
    );
};


interface WeightSliderProps {
    domain: WeightDomain;
    value: number;
    onChange: (value: number) => void;
    compact?: boolean;
}

const WeightSlider: React.FC<WeightSliderProps> = ({
    domain,
    value,
    onChange,
    compact = false,
}) => {
    const config = DOMAIN_CONFIG[domain];
    const percent = weightToPercent(value);
    
    // Handle slider input
    const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newPercent = parseInt(e.target.value, 10);
        onChange(newPercent / 100);
    };
    
    return (
        <div style={sliderContainerStyle}>
            {/* Label Row */}
            <div style={sliderLabelRowStyle}>
                <div style={sliderLabelStyle}>
                    <span style={sliderIconStyle}>{config.icon}</span>
                    <span style={sliderNameStyle}>{compact ? config.shortLabel : config.label}</span>
                </div>
                <span style={{ ...sliderValueStyle, color: config.color }}>
                    {percent}%
                </span>
            </div>
            
            {/* Slider Input */}
            <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={percent}
                onChange={handleInput}
                style={{
                    ...sliderInputStyle,
                    // Custom track color
                    background: `linear-gradient(to right, ${config.color} 0%, ${config.color} ${percent}%, #e5e7eb ${percent}%, #e5e7eb 100%)`,
                }}
                aria-label={`${config.label} weight: ${percent}%`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={percent}
            />
            
            {/* Description (non-compact only) */}
            {!compact && (
                <p style={sliderDescriptionStyle}>{config.description}</p>
            )}
        </div>
    );
};


// ---------------------------------------------------------------------------
// STYLES
// ---------------------------------------------------------------------------

const containerStyle: React.CSSProperties = {
    padding: '24px',
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    maxWidth: '600px',
};

const compactContainerStyle: React.CSSProperties = {
    padding: '16px',
    maxWidth: '400px',
};

const loadingStyle: React.CSSProperties = {
    padding: '40px',
    textAlign: 'center',
    color: '#6b7280',
};

const headerStyle: React.CSSProperties = {
    marginBottom: '20px',
};

const titleStyle: React.CSSProperties = {
    margin: '0 0 8px 0',
    fontSize: '1.5rem',
    fontWeight: 600,
    color: '#111827',
};

const subtitleStyle: React.CSSProperties = {
    margin: 0,
    color: '#6b7280',
    fontSize: '0.875rem',
};

// Budget Indicator Styles
const budgetContainerStyle: React.CSSProperties = {
    marginBottom: '20px',
    padding: '16px',
    backgroundColor: '#f9fafb',
    borderRadius: '8px',
};

const budgetHeaderStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
};

const budgetLabelStyle: React.CSSProperties = {
    fontSize: '0.875rem',
    color: '#374151',
    fontWeight: 500,
};

const budgetValueStyle: React.CSSProperties = {
    fontSize: '1.25rem',
    fontWeight: 700,
};

const progressBarContainerStyle: React.CSSProperties = {
    position: 'relative',
    height: '8px',
    backgroundColor: '#e5e7eb',
    borderRadius: '4px',
    overflow: 'hidden',
};

const progressBarFillStyle: React.CSSProperties = {
    position: 'absolute',
    left: 0,
    top: 0,
    height: '100%',
    borderRadius: '4px',
    transition: 'width 0.2s ease, background-color 0.2s ease',
};

const progressMarkerStyle: React.CSSProperties = {
    position: 'absolute',
    left: '100%',
    top: '-2px',
    width: '2px',
    height: '12px',
    backgroundColor: '#374151',
    transform: 'translateX(-1px)',
};

const budgetStatusStyle: React.CSSProperties = {
    marginTop: '8px',
    fontSize: '0.75rem',
    fontWeight: 500,
};

// Toggle Styles
const toggleContainerStyle: React.CSSProperties = {
    marginBottom: '20px',
};

const toggleLabelStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    cursor: 'pointer',
    fontSize: '0.875rem',
    color: '#374151',
};

const checkboxStyle: React.CSSProperties = {
    width: '16px',
    height: '16px',
    cursor: 'pointer',
};

const toggleHintStyle: React.CSSProperties = {
    display: 'block',
    marginTop: '4px',
    marginLeft: '24px',
    color: '#9ca3af',
    fontSize: '0.75rem',
};

// Slider Styles
const slidersContainerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
    marginBottom: '24px',
};

const sliderContainerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
};

const sliderLabelRowStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
};

const sliderLabelStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
};

const sliderIconStyle: React.CSSProperties = {
    fontSize: '1.25rem',
};

const sliderNameStyle: React.CSSProperties = {
    fontSize: '0.875rem',
    fontWeight: 500,
    color: '#374151',
};

const sliderValueStyle: React.CSSProperties = {
    fontSize: '1rem',
    fontWeight: 700,
};

const sliderInputStyle: React.CSSProperties = {
    width: '100%',
    height: '8px',
    borderRadius: '4px',
    appearance: 'none',
    cursor: 'pointer',
    outline: 'none',
};

const sliderDescriptionStyle: React.CSSProperties = {
    margin: '6px 0 0 0',
    fontSize: '0.75rem',
    color: '#9ca3af',
};

// Error Styles
const errorStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 16px',
    marginBottom: '16px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    color: '#dc2626',
    fontSize: '0.875rem',
};

const errorIconStyle: React.CSSProperties = {
    fontSize: '1rem',
};

// Button Styles
const actionsStyle: React.CSSProperties = {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap',
};

const buttonStyle: React.CSSProperties = {
    padding: '10px 20px',
    borderRadius: '6px',
    fontSize: '0.875rem',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    border: 'none',
};

const primaryButtonStyle: React.CSSProperties = {
    backgroundColor: '#3b82f6',
    color: 'white',
};

const secondaryButtonStyle: React.CSSProperties = {
    backgroundColor: '#f3f4f6',
    color: '#374151',
};

const tertiaryButtonStyle: React.CSSProperties = {
    backgroundColor: 'transparent',
    color: '#6b7280',
    textDecoration: 'underline',
};

const disabledButtonStyle: React.CSSProperties = {
    opacity: 0.5,
    cursor: 'not-allowed',
};

const validationHintStyle: React.CSSProperties = {
    marginTop: '12px',
    fontSize: '0.875rem',
    color: '#f59e0b',
    fontStyle: 'italic',
};


// ---------------------------------------------------------------------------
// CSS for slider thumb (inject into document)
// ---------------------------------------------------------------------------

if (typeof document !== 'undefined') {
    const styleId = 'strategy-tuner-styles';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .strategy-tuner input[type="range"]::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 20px;
                height: 20px;
                background: white;
                border: 2px solid #3b82f6;
                border-radius: 50%;
                cursor: pointer;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .strategy-tuner input[type="range"]::-moz-range-thumb {
                width: 20px;
                height: 20px;
                background: white;
                border: 2px solid #3b82f6;
                border-radius: 50%;
                cursor: pointer;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .strategy-tuner input[type="range"]:focus::-webkit-slider-thumb {
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
            }
        `;
        document.head.appendChild(style);
    }
}


export default StrategyTuner;
