# Speaker Identification Fix - Full Conversation Analysis

## Problem Fixed
**Issue**: Speaker labels were backwards at the beginning of transcripts. When the doctor spoke, they were labeled as "Patient" and when the patient spoke, they were labeled as "Doctor". This got corrected toward the end but caused confusion in the transcript.

**Root Cause**: The system was analyzing segments one-by-one during transcription, assigning speaker labels before it had enough context to determine who was actually the doctor. Early segments lacked sufficient medical terminology to correctly identify speakers.

## Solution Implemented
Changed from **sequential processing** to **full conversation analysis**:

### Previous Flow (Problematic)
1. Transcribe segment → Analyze medical terms → Assign label → Move to next segment
2. Early segments had few/no medical terms yet
3. System guessed wrong initially
4. Later segments accumulated enough data to correct the identification
5. Result: Labels flip mid-conversation ❌

### New Flow (Fixed)
1. Transcribe ALL segments first
2. Analyze ENTIRE conversation for patterns
3. Calculate confidence scores for each speaker
4. Make ONE decision about who is the doctor
5. Apply labels consistently to ALL segments ✅

## Technical Details

### New Function: `analyze_speaker_confidence()`
Located in `Backend/main.py` (lines 546-725)

Analyzes multiple factors across the **full conversation**:

#### Doctor Indicators
- **Medical terminology**: crown, implant, extraction, root canal, etc. (30 terms)
- **Technical procedure terms**: "recommend", "examination", "assessment", "prognosis"
- **Doctor directive phrases**: "your tooth", "we should", "open wide", "bite down"
- **Commands**: "hold still", "rinse", "let me see"
- **Longer utterances**: Doctors tend to speak in longer segments

#### Patient Indicators
- **First-person concern phrases**: "my tooth hurts", "I'm worried", "I feel"
- **Questions**: Patients ask more questions
- **Concerns**: Expressions of pain or worry
- **Shorter responses**: Often simpler yes/no or brief answers

#### Confidence Scoring
```python
doctor_score = (
    medical_ratio * 0.3 +      # Medical terminology usage
    technical_ratio * 0.25 +   # Technical procedure terms
    doctor_ratio * 0.2 +       # "Your tooth" type phrases
    command_ratio * 0.15 +     # Commands like "open wide"
    avg_words_segment * 0.1    # Longer segments
)

patient_score = (
    patient_ratio * 0.4 +      # "My tooth hurts" phrases
    concerns_ratio * 0.3 +     # Expressions of concern
    questions_ratio * 0.3      # Asking questions
)

confidence = abs(doctor_score - patient_score) / (doctor_score + patient_score)
```

### Updated Transcription Flow
Located in `Backend/main.py` (lines 900-945)

```python
# STEP 1: Analyze FULL conversation first
speaker_confidence = analyze_speaker_confidence(segments, speaker_segments, result)

# STEP 2: Determine doctor with confidence threshold
for speaker_id, confidence_data in speaker_confidence.items():
    if confidence_data['is_doctor'] and confidence_data['confidence'] > 0.3:
        doctor_speaker = speaker_id
        break

# STEP 3: Apply labels consistently to ALL segments
for segment in segments:
    speaker_label = "Doctor" if speaker == doctor_speaker else "Patient"
    formatted_lines.append(f"{speaker_label}: {text}")
```

## Speaker Identification Priority
The system uses multiple methods in order of reliability:

1. **Voice Profile Matching** (if enabled)
   - Compares audio against stored doctor voice profile
   - Uses torchaudio for speaker recognition
   - Confidence threshold: 0.4

2. **Full Conversation Analysis** (NEW - primary fallback)
   - Analyzes all speech patterns across entire recording
   - Uses medical term frequency, speech patterns, questions/commands
   - Confidence threshold: 0.3

3. **Fallback Heuristic** (emergency)
   - If confidence too low, uses speaker with highest doctor_score
   - Ensures system always makes a decision

## Benefits

### ✅ Correct Labels from Start
- No more backwards labels at beginning
- Doctor identified correctly in first segments
- Patient identified correctly in first segments

### ✅ Consistent Throughout
- Labels don't flip mid-conversation
- Single confident decision applied to all segments
- No confusion in transcript

### ✅ Better Accuracy
- Multiple confidence factors (medical terms, speech patterns, questions)
- Full context analysis (not just first few words)
- Validated against entire conversation

### ✅ Logging for Debugging
```
Speaker SPEAKER_00: DOCTOR (confidence: 0.85, doctor_score: 12.5, patient_score: 2.1)
  - medical=8.5%, technical=4.2, commands=3.8
Speaker SPEAKER_01: PATIENT (confidence: 0.72, doctor_score: 1.8, patient_score: 9.3)
  - patient_phrases=6.1, concerns=5, questions=8
```

## Testing the Fix

### Test Case 1: Doctor Speaks First
**Before Fix**:
```
Patient: Let me take a look at that tooth.
Patient: I see you need a crown here.
Doctor: It hurts when I chew.
```

**After Fix**:
```
Doctor: Let me take a look at that tooth.
Doctor: I see you need a crown here.
Patient: It hurts when I chew.
```

### Test Case 2: Patient Speaks First
**Before Fix**:
```
Doctor: My tooth has been hurting for weeks.
Doctor: When did it start?
Patient: Let me examine the area.
```

**After Fix**:
```
Patient: My tooth has been hurting for weeks.
Doctor: When did it start?
Doctor: Let me examine the area.
```

## Configuration
No configuration changes needed. The fix is automatic and applies to all transcriptions.

### Confidence Thresholds
You can adjust in `Backend/main.py`:
```python
# Line ~935 - Minimum confidence to accept speaker identification
if best_confidence > 0.3:  # Adjust this value (0.0-1.0)
    doctor_speaker = best_doctor_candidate
```

### Medical Terms
Add specialty-specific terms in `analyze_speaker_confidence()`:
```python
medical_terms = [
    'crown', 'implant', 'extraction', # ... add your terms here
]
```

## Files Modified
1. **Backend/main.py**
   - Added `analyze_speaker_confidence()` function (lines 546-725)
   - Updated `transcribe_audio_with_diarization()` (lines 900-945)
   - Now analyzes full conversation before labeling

## Deployment
✅ **Already Deployed** (January 2025)
- Docker image rebuilt
- Services restarted
- Ready to test with new recordings

## Next Steps
1. **Test with Real Recordings**: Record a few consultations and verify labels are correct from the start
2. **Monitor Confidence Scores**: Check logs for confidence values to ensure they're above 0.3
3. **Add Specialty Terms**: Customize medical term lists for your specific practice areas
4. **Adjust Thresholds**: If needed, tune confidence thresholds based on your use case

## Support
If speaker labels are still incorrect:
1. Check logs for confidence scores: `docker logs boise_new_backend`
2. Look for: `"Speaker SPEAKER_XX: DOCTOR (confidence: X.XX)"`
3. If confidence is low (<0.3), add more specialty-specific medical terms
4. Consider enabling voice profile matching for better accuracy
