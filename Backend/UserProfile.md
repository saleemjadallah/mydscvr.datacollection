# Dubai Events App - Onboarding & Profile Implementation

This document provides a comprehensive implementation guide for creating an engaging onboarding flow and user profile page for the Dubai Events app.

## Overview

The onboarding process collects family preferences after signup to personalize event recommendations through your AI system. The user profile allows users to manage these preferences and family information.

## 1. Onboarding Flow Structure

1. **Welcome Screen** - Brief introduction to personalization
2. **Family Setup** - Add family members and their ages
3. **Interest Selection** - Choose categories of events they enjoy
4. **Location Preferences** - Select preferred Dubai areas 
5. **Budget & Schedule** - Set price ranges and preferred days/times
6. **Completion Screen** - Success message and entry to main app

## 2. Core Implementation

### Onboarding Controller

```dart
// features/onboarding/onboarding_controller.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

class OnboardingState {
  final int currentStep;
  final Map<String, dynamic> preferences;
  final List<FamilyMember> familyMembers;
  final bool isCompleted;
  
  const OnboardingState({
    this.currentStep = 0,
    this.preferences = const {},
    this.familyMembers = const [],
    this.isCompleted = false,
  });
  
  OnboardingState copyWith({
    int? currentStep,
    Map<String, dynamic>? preferences,
    List<FamilyMember>? familyMembers,
    bool? isCompleted,
  }) {
    return OnboardingState(
      currentStep: currentStep ?? this.currentStep,
      preferences: preferences ?? Map.from(this.preferences),
      familyMembers: familyMembers ?? List.from(this.familyMembers),
      isCompleted: isCompleted ?? this.isCompleted,
    );
  }
}

class FamilyMember {
  final String id;
  final String name;
  final int age;
  final String relationship;
  final String? avatarSeed; // Used for Dicebear avatar generation
  
  const FamilyMember({
    required this.id,
    required this.name,
    required this.age,
    required this.relationship,
    this.avatarSeed,
  });
}

class OnboardingNotifier extends StateNotifier<OnboardingState> {
  OnboardingNotifier() : super(const OnboardingState());
  
  void nextStep() {
    state = state.copyWith(currentStep: state.currentStep + 1);
  }
  
  void previousStep() {
    if (state.currentStep > 0) {
      state = state.copyWith(currentStep: state.currentStep - 1);
    }
  }
  
  void addFamilyMember(FamilyMember member) {
    state = state.copyWith(
      familyMembers: [...state.familyMembers, member],
    );
  }
  
  void removeFamilyMember(String id) {
    state = state.copyWith(
      familyMembers: state.familyMembers.where((m) => m.id != id).toList(),
    );
  }
  
  void updatePreference(String key, dynamic value) {
    final updatedPreferences = Map<String, dynamic>.from(state.preferences);
    updatedPreferences[key] = value;
    
    state = state.copyWith(preferences: updatedPreferences);
  }
  
  void completeOnboarding() {
    state = state.copyWith(isCompleted: true);
    // Save preferences to backend/local storage
    savePreferences();
  }
  
  Future<void> savePreferences() async {
    // Implementation for saving to backend/local storage
    // This would connect to your API client or shared preferences
  }
}

final onboardingProvider = StateNotifierProvider<OnboardingNotifier, OnboardingState>(
  (ref) => OnboardingNotifier(),
);
```

### Main Onboarding Screen

```dart
// features/onboarding/onboarding_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';

class OnboardingScreen extends ConsumerWidget {
  const OnboardingScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final onboardingState = ref.watch(onboardingProvider);
    
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // Progress bar
            _buildProgressBar(context, onboardingState.currentStep),
            
            // Main content
            Expanded(
              child: PageView(
                physics: const NeverScrollableScrollPhysics(),
                controller: PageController(initialPage: onboardingState.currentStep),
                onPageChanged: (page) {
                  ref.read(onboardingProvider.notifier).state = 
                      onboardingState.copyWith(currentStep: page);
                },
                children: [
                  WelcomeStep(),
                  FamilySetupStep(),
                  InterestsStep(),
                  LocationPreferencesStep(),
                  BudgetScheduleStep(),
                  CompletionStep(),
                ],
              ),
            ),
            
            // Navigation buttons
            _buildNavigationButtons(context, ref, onboardingState),
          ],
        ),
      ),
    );
  }
  
  Widget _buildProgressBar(BuildContext context, int currentStep) {
    final totalSteps = 5; // Excluding completion screen
    
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Row(
        children: List.generate(totalSteps, (index) {
          final isActive = index <= currentStep;
          final isCompleted = index < currentStep;
          
          return Expanded(
            child: Container(
              height: 4,
              margin: EdgeInsets.only(right: index < totalSteps - 1 ? 8 : 0),
              decoration: BoxDecoration(
                color: isActive 
                    ? AppColors.dubaiTeal 
                    : Colors.grey.withOpacity(0.3),
                borderRadius: BorderRadius.circular(2),
              ),
              child: isCompleted
                  ? Container(
                      decoration: BoxDecoration(
                        color: AppColors.dubaiTeal,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    )
                  : null,
            ),
          );
        }),
      ),
    ).animate().fadeIn();
  }
  
  Widget _buildNavigationButtons(
    BuildContext context, 
    WidgetRef ref, 
    OnboardingState state
  ) {
    final isLastStep = state.currentStep == 4; // Before completion screen
    
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          if (state.currentStep > 0)
            Expanded(
              child: OutlinedButton(
                onPressed: () => ref.read(onboardingProvider.notifier).previousStep(),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(28),
                  ),
                  side: const BorderSide(color: AppColors.dubaiTeal),
                ),
                child: Text(
                  'Back',
                  style: GoogleFonts.poppins(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: AppColors.dubaiTeal,
                  ),
                ),
              ),
            ),
          
          if (state.currentStep > 0) const SizedBox(width: 16),
          
          Expanded(
            flex: state.currentStep == 0 ? 1 : 2,
            child: ElevatedButton(
              onPressed: () {
                if (isLastStep) {
                  ref.read(onboardingProvider.notifier).completeOnboarding();
                  ref.read(onboardingProvider.notifier).nextStep();
                } else if (state.currentStep == 5) { // Completion screen
                  context.go('/home');
                } else {
                  ref.read(onboardingProvider.notifier).nextStep();
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.dubaiTeal,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(28),
                ),
              ),
              child: Text(
                isLastStep ? 'Finish' : 
                (state.currentStep == 5 ? 'Get Started!' : 'Continue'),
                style: GoogleFonts.poppins(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
```

## 3. Individual Onboarding Steps

### Step 1: Welcome Screen

```dart
// features/onboarding/steps/welcome_step.dart
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';

class WelcomeStep extends StatelessWidget {
  const WelcomeStep({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Animated welcome icon
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              gradient: AppColors.sunsetGradient,
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.family_restroom,
              color: Colors.white,
              size: 64,
            ),
          ).animate().scale(
            duration: const Duration(milliseconds: 600),
            curve: Curves.elasticOut,
          ),
          
          const SizedBox(height: 40),
          
          // Welcome text
          Text(
            'Personalize Your Experience',
            style: GoogleFonts.comfortaa(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
            textAlign: TextAlign.center,
          ).animate().fadeIn(delay: 300.ms),
          
          const SizedBox(height: 16),
          
          Text(
            'Let\'s set up your family profile to find the perfect Dubai events for you!',
            style: GoogleFonts.inter(
              fontSize: 16,
              color: AppColors.textSecondary,
              height: 1.5,
            ),
            textAlign: TextAlign.center,
          ).animate().fadeIn(delay: 500.ms),
          
          const SizedBox(height: 40),
          
          // Benefits list
          ..._buildBenefitItems().animate(
            interval: 200.ms,
          ).fadeInUp(
            duration: 600.ms,
            curve: Curves.easeOutQuad,
          ),
        ],
      ),
    );
  }
  
  List<Widget> _buildBenefitItems() {
    final benefits = [
      {'icon': Icons.family_restroom, 'text': 'Find age-appropriate events'},
      {'icon': Icons.location_on, 'text': 'Discover events in your favorite areas'},
      {'icon': Icons.interests, 'text': 'Match activities to your family\'s interests'},
      {'icon': Icons.watch_later, 'text': 'Get personalized recommendations'},
    ];
    
    return benefits.map((benefit) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.dubaiTeal.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                benefit['icon'] as IconData,
                color: AppColors.dubaiTeal,
                size: 24,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Text(
                benefit['text'] as String,
                style: GoogleFonts.inter(
                  fontSize: 16,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
          ],
        ),
      );
    }).toList();
  }
}
```

### Step 2: Family Setup

```dart
// features/onboarding/steps/family_setup_step.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:uuid/uuid.dart';

class FamilySetupStep extends ConsumerStatefulWidget {
  const FamilySetupStep({Key? key}) : super(key: key);
  
  @override
  ConsumerState<FamilySetupStep> createState() => _FamilySetupStepState();
}

class _FamilySetupStepState extends ConsumerState<FamilySetupStep> {
  final _nameController = TextEditingController();
  int _selectedAge = 30;
  String _selectedRelationship = 'Parent';
  
  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    final familyMembers = ref.watch(onboardingProvider).familyMembers;
    
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Create Your Family Profile',
            style: GoogleFonts.comfortaa(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ).animate().fadeIn(),
          
          const SizedBox(height: 8),
          
          Text(
            'Add family members to personalize event recommendations',
            style: GoogleFonts.inter(
              fontSize: 16,
              color: AppColors.textSecondary,
            ),
          ).animate().fadeIn(delay: 200.ms),
          
          const SizedBox(height: 32),
          
          // Family members list
          if (familyMembers.isNotEmpty) ...[
            Text(
              'Family Members',
              style: GoogleFonts.poppins(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            
            const SizedBox(height: 16),
            
            ...familyMembers.map((member) => _buildFamilyMemberCard(member)).toList(),
            
            const SizedBox(height: 24),
          ],
          
          // Add new member form
          _buildAddMemberForm(),
        ],
      ),
    );
  }
  
  Widget _buildFamilyMemberCard(FamilyMember member) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          // Avatar
          _buildAvatar(member.name, member.avatarSeed),
          
          const SizedBox(width: 16),
          
          // Member info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  member.name,
                  style: GoogleFonts.poppins(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  '${member.relationship} • ${member.age} years old',
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          
          // Delete button
          IconButton(
            onPressed: () {
              ref.read(onboardingProvider.notifier).removeFamilyMember(member.id);
            },
            icon: const Icon(
              Icons.delete_outline,
              color: Colors.red,
              size: 20,
            ),
          ),
        ],
      ),
    ).animate().fadeIn();
  }
  
  Widget _buildAddMemberForm() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Add Family Member',
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          
          const SizedBox(height: 20),
          
          // Name field
          TextField(
            controller: _nameController,
            decoration: InputDecoration(
              labelText: 'Name',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              prefixIcon: const Icon(Icons.person),
            ),
          ),
          
          const SizedBox(height: 20),
          
          // Age slider
          Text(
            'Age: $_selectedAge years',
            style: GoogleFonts.poppins(
              fontSize: 16,
              fontWeight: FontWeight.w500,
              color: AppColors.textPrimary,
            ),
          ),
          
          Slider(
            value: _selectedAge.toDouble(),
            min: 0,
            max: 80,
            divisions: 80,
            activeColor: AppColors.dubaiTeal,
            label: _selectedAge.toString(),
            onChanged: (value) {
              setState(() {
                _selectedAge = value.toInt();
              });
            },
          ),
          
          const SizedBox(height: 20),
          
          // Relationship dropdown
          DropdownButtonFormField<String>(
            value: _selectedRelationship,
            decoration: InputDecoration(
              labelText: 'Relationship',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              prefixIcon: const Icon(Icons.family_restroom),
            ),
            items: ['Parent', 'Child', 'Grandparent', 'Other'].map((String value) {
              return DropdownMenuItem<String>(
                value: value,
                child: Text(value),
              );
            }).toList(),
            onChanged: (value) {
              setState(() {
                _selectedRelationship = value!;
              });
            },
          ),
          
          const SizedBox(height: 24),
          
          // Add button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _addFamilyMember,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.dubaiTeal,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              icon: const Icon(Icons.add),
              label: Text(
                'Add Member',
                style: GoogleFonts.poppins(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
      ),
    ).animate().fadeIn(delay: 400.ms);
  }
  
  void _addFamilyMember() {
    if (_nameController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a name')),
      );
      return;
    }
    
    final uuid = const Uuid();
    final member = FamilyMember(
      id: uuid.v4(),
      name: _nameController.text.trim(),
      age: _selectedAge,
      relationship: _selectedRelationship,
      avatarSeed: _nameController.text.trim(), // Use name as seed for avatar
    );
    
    ref.read(onboardingProvider.notifier).addFamilyMember(member);
    _nameController.clear();
    setState(() {
      _selectedAge = 30;
      _selectedRelationship = 'Parent';
    });
  }
  
  Widget _buildAvatar(String name, String? seed) {
    // Using Dicebear Avatars API for beautiful, diverse avatars
    final avatarUrl = 'https://api.dicebear.com/7.x/avataaars/svg?seed=${seed ?? name}';
    
    return Container(
      width: 50,
      height: 50,
      decoration: BoxDecoration(
        color: AppColors.dubaiTeal.withOpacity(0.1),
        shape: BoxShape.circle,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(25),
        child: Image.network(
          avatarUrl,
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) {
            return CircleAvatar(
              backgroundColor: AppColors.dubaiTeal,
              child: Text(
                name.isNotEmpty ? name[0].toUpperCase() : '?',
                style: const TextStyle(color: Colors.white),
              ),
            );
          },
        ),
      ),
    );
  }
}
```

### Step 3: Interests Selection

```dart
// features/onboarding/steps/interests_step.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';

class InterestsStep extends ConsumerStatefulWidget {
  const InterestsStep({Key? key}) : super(key: key);
  
  @override
  ConsumerState<InterestsStep> createState() => _InterestsStepState();
}

class _InterestsStepState extends ConsumerState<InterestsStep> {
  final List<String> _selectedInterests = [];
  
  final List<Map<String, dynamic>> _interestCategories = [
    {
      'title': 'Activities',
      'interests': [
        {'name': 'Outdoor Adventures', 'icon': Icons.hiking},
        {'name': 'Sports Events', 'icon': Icons.sports_soccer},
        {'name': 'Swimming', 'icon': Icons.pool},
        {'name': 'Arts & Crafts', 'icon': Icons.color_lens},
        {'name': 'Music & Dance', 'icon': Icons.music_note},
      ],
    },
    {
      'title': 'Learning',
      'interests': [
        {'name': 'Educational Workshops', 'icon': Icons.school},
        {'name': 'Science & Technology', 'icon': Icons.science},
        {'name': 'Cultural Experiences', 'icon': Icons.language},
        {'name': 'Museums & Exhibitions', 'icon': Icons.museum},
        {'name': 'Reading & Storytelling', 'icon': Icons.book},
      ],
    },
    {
      'title': 'Entertainment',
      'interests': [
        {'name': 'Theme Parks', 'icon': Icons.attractions},
        {'name': 'Movies & Shows', 'icon': Icons.movie},
        {'name': 'Gaming', 'icon': Icons.sports_esports},
        {'name': 'Food Experiences', 'icon': Icons.restaurant},
        {'name': 'Shopping', 'icon': Icons.shopping_bag},
      ],
    },
    {
      'title': 'Nature & Animals',
      'interests': [
        {'name': 'Parks & Gardens', 'icon': Icons.park},
        {'name': 'Beaches', 'icon': Icons.beach_access},
        {'name': 'Wildlife & Zoos', 'icon': Icons.pets},
        {'name': 'Desert Activities', 'icon': Icons.terrain},
        {'name': 'Boating & Fishing', 'icon': Icons.sailing},
      ],
    },
  ];
  
  @override
  void initState() {
    super.initState();
    
    // Initialize with any existing preferences
    final existingInterests = ref.read(onboardingProvider).preferences['interests'] as List<String>?;
    if (existingInterests != null) {
      _selectedInterests.addAll(existingInterests);
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'What do you enjoy?',
            style: GoogleFonts.comfortaa(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ).animate().fadeIn(),
          
          const SizedBox(height: 8),
          
          Text(
            'Select activities your family loves to do together',
            style: GoogleFonts.inter(
              fontSize: 16,
              color: AppColors.textSecondary,
            ),
          ).animate().fadeIn(delay: 200.ms),
          
          const SizedBox(height: 32),
          
          // Selected interests count
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: AppColors.dubaiTeal.withOpacity(0.1),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Text(
              'Selected: ${_selectedInterests.length} interests',
              style: GoogleFonts.poppins(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: AppColors.dubaiTeal,
              ),
            ),
          ).animate().fadeIn(delay: 300.ms),
          
          const SizedBox(height: 24),
          
          // Categories
          ..._interestCategories.map((category) {
            return _buildCategorySection(
              category['title'] as String,
              category['interests'] as List<Map<String, dynamic>>,
            );
          }).toList(),
        ],
      ),
    );
  }
  
  Widget _buildCategorySection(String title, List<Map<String, dynamic>> interests) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ).animate().fadeIn(delay: 400.ms),
          
          const SizedBox(height: 16),
          
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: interests.map((interest) {
              final interestName = interest['name'] as String;
              final isSelected = _selectedInterests.contains(interestName);
              
              return GestureDetector(
                onTap: () {
                  setState(() {
                    if (isSelected) {
                      _selectedInterests.remove(interestName);
                    } else {
                      _selectedInterests.add(interestName);
                    }
                  });
                  
                  // Update preferences
                  ref.read(onboardingProvider.notifier).updatePreference(
                    'interests',
                    _selectedInterests,
                  );
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: isSelected 
                        ? AppColors.dubaiTeal
                        : Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: isSelected
                          ? Colors.transparent
                          : Colors.grey.withOpacity(0.3),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.05),
                        blurRadius: 5,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        interest['icon'] as IconData,
                        size: 20,
                        color: isSelected ? Colors.white : AppColors.dubaiTeal,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        interestName,
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: isSelected ? Colors.white : AppColors.textPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
              ).animate().fadeIn(
                delay: Duration(milliseconds: 500 + interests.indexOf(interest) * 100),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
```

### Step 4: Location Preferences

```dart
// features/onboarding/steps/location_preferences_step.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';

class LocationPreferencesStep extends ConsumerStatefulWidget {
  const LocationPreferencesStep({Key? key}) : super(key: key);
  
  @override
  ConsumerState<LocationPreferencesStep> createState() => _LocationPreferencesStepState();
}

class _LocationPreferencesStepState extends ConsumerState<LocationPreferencesStep> {
  final List<String> _selectedLocations = [];
  double _maxTravelDistance = 20.0; // km
  
  final List<Map<String, dynamic>> _dubaiAreas = [
    {'name': 'Dubai Marina', 'icon': Icons.sailing},
    {'name': 'JBR', 'icon': Icons.beach_access},
    {'name': 'Downtown Dubai', 'icon': Icons.location_city},
    {'name': 'Palm Jumeirah', 'icon': Icons.terrain},
    {'name': 'Jumeirah', 'icon': Icons.villa},
    {'name': 'Business Bay', 'icon': Icons.business},
    {'name': 'Dubai Hills', 'icon': Icons.landscape},
    {'name': 'Arabian Ranches', 'icon': Icons.home},
    {'name': 'Al Barsha', 'icon': Icons.apartment},
    {'name': 'Mirdif', 'icon': Icons.house},
    {'name': 'Dubai Silicon Oasis', 'icon': Icons.computer},
    {'name': 'Dubai Festival City', 'icon': Icons.celebration},
    {'name': 'Motor City', 'icon': Icons.directions_car},
    {'name': 'Dubai Creek', 'icon': Icons.water},
    {'name': 'Deira', 'icon': Icons.store},
    {'name': 'DIFC', 'icon': Icons.attach_money},
  ];
  
  @override
  void initState() {
    super.initState();
    
    // Initialize with any existing preferences
    final existingLocations = ref.read(onboardingProvider).preferences['preferredLocations'] as List<String>?;
    if (existingLocations != null) {
      _selectedLocations.addAll(existingLocations);
    }
    
    final existingDistance = ref.read(onboardingProvider).preferences['maxTravelDistance'] as double?;
    if (existingDistance != null) {
      _maxTravelDistance = existingDistance;
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Where in Dubai?',
            style: GoogleFonts.comfortaa(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ).animate().fadeIn(),
          
          const SizedBox(height: 8),
          
          Text(
            'Select areas in Dubai where you prefer to attend events',
            style: GoogleFonts.inter(
              fontSize: 16,
              color: AppColors.textSecondary,
            ),
          ).animate().fadeIn(delay: 200.ms),
          
          const SizedBox(height: 32),
          
          // Map visualization would go here
          Container(
            height: 180,
            width: double.infinity,
            decoration: BoxDecoration(
              color: Colors.grey[200],
              borderRadius: BorderRadius.circular(20),
              image: const DecorationImage(
                image: AssetImage('assets/images/dubai_map.png'),
                fit: BoxFit.cover,
              ),
            ),
            child: Center(
              child: Text(
                'Dubai',
                style: GoogleFonts.comfortaa(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  color: Colors.white.withOpacity(0.7),
                ),
              ),
            ),
          ).animate().fadeIn(delay: 300.ms),
          
          const SizedBox(height: 32),
          
          // Max travel distance
          Text(
            'Maximum Travel Distance',
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ).animate().fadeIn(delay: 400.ms),
          
          const SizedBox(height: 8),
          
          Text(
            'How far are you willing to travel for events?',
            style: GoogleFonts.inter(
              fontSize: 14,
              color: AppColors.textSecondary,
            ),
          ).animate().fadeIn(delay: 500.ms),
          
          const SizedBox(height: 16),
          
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '5 km',
                style: GoogleFonts.inter(
                  fontSize: 14,
                  color: AppColors.textSecondary,
                ),
              ),
              Text(
                '50 km',
                style: GoogleFonts.inter(
                  fontSize: 14,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          
          Slider(
            value: _maxTravelDistance,
            min: 5,
            max: 50,
            divisions: 9,
            activeColor: AppColors.dubaiTeal,
            label: '${_maxTravelDistance.toInt()} km',
            onChanged: (value) {
              setState(() {
                _maxTravelDistance = value;
              });
              
              // Update preferences
              ref.read(onboardingProvider.notifier).updatePreference(
                'maxTravelDistance',
                _maxTravelDistance,
              );
            },
          ),
          
          Center(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.dubaiTeal.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                '${_maxTravelDistance.toInt()} kilometers',
                style: GoogleFonts.poppins(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: AppColors.dubaiTeal,
                ),
              ),
            ),
          ).animate().fadeIn(delay: 600.ms),
          
          const SizedBox(height: 32),
          
          // Dubai areas
          Text(
            'Preferred Areas',
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ).animate().fadeIn(delay: 700.ms),
          
          const SizedBox(height: 8),
          
          Text(
            'Select areas where you typically attend events',
            style: GoogleFonts.inter(
              fontSize: 14,
              color: AppColors.textSecondary,
            ),
          ).animate().fadeIn(delay: 800.ms),
          
          const SizedBox(height: 16),
          
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: _dubaiAreas.map((area) {
              final areaName = area['name'] as String;
              final isSelected = _selectedLocations.contains(areaName);
              
              return GestureDetector(
                onTap: () {
                  setState(() {
                    if (isSelected) {
                      _selectedLocations.remove(areaName);
                    } else {
                      _selectedLocations.add(areaName);
                    }
                  });
                  
                  // Update preferences
                  ref.read(onboardingProvider.notifier).updatePreference(
                    'preferredLocations',
                    _selectedLocations,
                  );
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: isSelected 
                        ? AppColors.dubaiTeal
                        : Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: isSelected
                          ? Colors.transparent
                          : Colors.grey.withOpacity(0.3),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.05),
                        blurRadius: 5,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        area['icon'] as IconData,
                        size: 20,
                        color: isSelected ? Colors.white : AppColors.dubaiTeal,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        areaName,
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: isSelected ? Colors.white : AppColors.textPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
              ).animate().fadeIn(
                delay: Duration(milliseconds: 900 + _dubaiAreas.indexOf(area) * 50),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
```

### Step 5: Budget & Schedule

```dart
// features/onboarding/steps/budget_schedule_step.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';

class BudgetScheduleStep extends ConsumerStatefulWidget {
  const BudgetScheduleStep({Key? key}) : super(key: key);
  
  @override
  ConsumerState<BudgetScheduleStep> createState() => _BudgetScheduleStepState();
}

class _BudgetScheduleStepState extends ConsumerState<BudgetScheduleStep> {
  RangeValues _priceRange = const RangeValues(0, 500);
  final List<String> _selectedDays = [];
  String _selectedTimePreference = 'Afternoon';
  
  final List<String> _daysOfWeek = [
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 
    'Friday', 'Saturday', 'Sunday'
  ];
  
  final List<String> _timePreferences = [
    'Morning', 'Afternoon', 'Evening', 'Night'
  ];
  
  @override
  void initState() {
    super.initState();
    
    // Initialize with any existing preferences
    final existingMinPrice = ref.read(onboardingProvider).preferences['minPrice'] as double?;
    final existingMaxPrice = ref.read(onboardingProvider).preferences['maxPrice'] as double?;
    
    if (existingMinPrice != null && existingMaxPrice != null) {
      _priceRange = RangeValues(existingMinPrice, existingMaxPrice);
    }
    
    final existingDays = ref.read(onboardingProvider).preferences['preferredDays'] as List<String>?;
    if (existingDays != null) {
      _selectedDays.addAll(existingDays);
    } else {
      // Default to weekends
      _selectedDays.addAll(['Friday', 'Saturday']);
    }
    
    final existingTime = ref.read(onboardingProvider).preferences['preferredTime'] as String?;
    if (existingTime != null) {
      _selectedTimePreference = existingTime;
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Budget & Availability',
            style: GoogleFonts.comfortaa(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ).animate().fadeIn(),
          
          const SizedBox(height: 8),
          
          Text(
            'Tell us about your budget and when you\'re available',
            style: GoogleFonts.inter(
              fontSize: 16,
              color: AppColors.textSecondary,
            ),
          ).animate().fadeIn(delay: 200.ms),
          
          const SizedBox(height: 32),
          
          // Budget section
          _buildBudgetSection().animate().fadeIn(delay: 300.ms),
          
          const SizedBox(height: 32),
          
          // Days section
          _buildDaysSection().animate().fadeIn(delay: 500.ms),
          
          const SizedBox(height: 32),
          
          // Time preference section
          _buildTimePreferenceSection().animate().fadeIn(delay: 700.ms),
        ],
      ),
    );
  }
  
  Widget _buildBudgetSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Event Budget',
          style: GoogleFonts.poppins(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
        
        const SizedBox(height: 8),
        
        Text(
          'What\'s your budget range for family events? (AED)',
          style: GoogleFonts.inter(
            fontSize: 14,
            color: AppColors.textSecondary,
          ),
        ),
        
        const SizedBox(height: 24),
        
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'AED ${_priceRange.start.toInt()}',
              style: GoogleFonts.poppins(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: AppColors.dubaiTeal,
              ),
            ),
            Text(
              'AED ${_priceRange.end.toInt()}',
              style: GoogleFonts.poppins(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: AppColors.dubaiTeal,
              ),
            ),
          ],
        ),
        
        RangeSlider(
          values: _priceRange,
          min: 0,
          max: 1000,
          divisions: 20,
          activeColor: AppColors.dubaiTeal,
          labels: RangeLabels(
            'AED ${_priceRange.start.round()}',
            'AED ${_priceRange.end.round()}',
          ),
          onChanged: (values) {
            setState(() {
              _priceRange = values;
            });
            
            // Update preferences
            ref.read(onboardingProvider.notifier).updatePreference(
              'minPrice',
              _priceRange.start,
            );
            
            ref.read(onboardingProvider.notifier).updatePreference(
              'maxPrice',
              _priceRange.end,
            );
          },
        ),
        
        const SizedBox(height: 8),
        
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Free',
              style: GoogleFonts.inter(
                fontSize: 14,
                color: AppColors.textSecondary,
              ),
            ),
            Text(
              'AED 1,000+',
              style: GoogleFonts.inter(
                fontSize: 14,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ],
    );
  }
  
  Widget _buildDaysSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Preferred Days',
          style: GoogleFonts.poppins(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
        
        const SizedBox(height: 8),
        
        Text(
          'When do you typically attend events?',
          style: GoogleFonts.inter(
            fontSize: 14,
            color: AppColors.textSecondary,
          ),
        ),
        
        const SizedBox(height: 16),
        
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: _daysOfWeek.map((day) {
            final isSelected = _selectedDays.contains(day);
            
            return GestureDetector(
              onTap: () {
                setState(() {
                  if (isSelected) {
                    _selectedDays.remove(day);
                  } else {
                    _selectedDays.add(day);
                  }
                });
                
                // Update preferences
                ref.read(onboardingProvider.notifier).updatePreference(
                  'preferredDays',
                  _selectedDays,
                );
              },
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
                decoration: BoxDecoration(
                  color: isSelected
                      ? AppColors.dubaiTeal
                      : Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: isSelected
                        ? Colors.transparent
                        : Colors.grey.withOpacity(0.3),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.05),
                      blurRadius: 5,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Text(
                  day.substring(0, 3),  // Abbreviate to first 3 letters
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: isSelected ? Colors.white : AppColors.textPrimary,
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
  
  Widget _buildTimePreferenceSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Preferred Time',
          style: GoogleFonts.poppins(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
        
        const SizedBox(height: 8),
        
        Text(
          'What time of day works best for your family?',
          style: GoogleFonts.inter(
            fontSize: 14,
            color: AppColors.textSecondary,
          ),
        ),
        
        const SizedBox(height: 16),
        
        Column(
          children: _timePreferences.map((time) {
            final isSelected = _selectedTimePreference == time;
            
            return Container(
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: isSelected
                    ? AppColors.dubaiTeal.withOpacity(0.1)
                    : Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: isSelected
                      ? AppColors.dubaiTeal
                      : Colors.grey.withOpacity(0.3),
                ),
              ),
              child: RadioListTile<String>(
                title: Text(
                  time,
                  style: GoogleFonts.inter(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                    color: isSelected ? AppColors.dubaiTeal : AppColors.textPrimary,
                  ),
                ),
                subtitle: Text(
                  _getTimeDescription(time),
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    color: AppColors.textSecondary,
                  ),
                ),
                value: time,
                groupValue: _selectedTimePreference,
                activeColor: AppColors.dubaiTeal,
                onChanged: (value) {
                  setState(() {
                    _selectedTimePreference = value!;
                  });
                  
                  // Update preferences
                  ref.read(onboardingProvider.notifier).updatePreference(
                    'preferredTime',
                    _selectedTimePreference,
                  );
                },
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
  
  String _getTimeDescription(String time) {
    switch (time) {
      case 'Morning':
        return '8 AM - 12 PM';
      case 'Afternoon':
        return '12 PM - 4 PM';
      case 'Evening':
        return '4 PM - 8 PM';
      case 'Night':
        return 'After 8 PM';
      default:
        return '';
    }
  }
}
```

### Step 6: Completion Screen

```dart
// features/onboarding/steps/completion_step.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:lottie/lottie.dart';

class CompletionStep extends ConsumerWidget {
  const CompletionStep({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final onboardingState = ref.watch(onboardingProvider);
    
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Success animation
          Lottie.network(
            'https://assets9.lottiefiles.com/packages/lf20_lk80fpsm.json',
            width: 200,
            height: 200,
            repeat: false,
          ),
          
          const SizedBox(height: 40),
          
          Text(
            'All Set!',
            style: GoogleFonts.comfortaa(
              fontSize: 32,
              fontWeight: FontWeight.bold,
              color: AppColors.dubaiTeal,
            ),
            textAlign: TextAlign.center,
          ).animate().fadeIn(delay: 300.ms),
          
          const SizedBox(height: 16),
          
          Text(
            'Your family profile is ready, and we\'re personalizing your event recommendations.',
            style: GoogleFonts.inter(
              fontSize: 16,
              color: AppColors.textSecondary,
              height: 1.5,
            ),
            textAlign: TextAlign.center,
          ).animate().fadeIn(delay: 500.ms),
          
          const SizedBox(height: 40),
          
          // Profile summary
          _buildProfileSummary(onboardingState).animate().fadeIn(delay: 700.ms),
        ],
      ),
    );
  }
  
  Widget _buildProfileSummary(OnboardingState state) {
    // Only show if we have family members
    if (state.familyMembers.isEmpty) {
      return const SizedBox();
    }
    
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Your Family Profile',
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Family members preview
          Row(
            children: [
              for (int i = 0; i < state.familyMembers.length; i++)
                if (i < 4) // Only show up to 4 members
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: _buildAvatarStack(state.familyMembers[i], i),
                  ),
              
              if (state.familyMembers.length > 4)
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: AppColors.dubaiCoral.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      '+${state.familyMembers.length - 4}',
                      style: GoogleFonts.poppins(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppColors.dubaiCoral,
                      ),
                    ),
                  ),
                ),
              
              const Spacer(),
              
              Text(
                '${state.familyMembers.length} members',
                style: GoogleFonts.inter(
                  fontSize: 14,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 16),
          
          // Divider
          const Divider(),
          
          const SizedBox(height: 16),
          
          // Interests preview
          _buildPreferenceSummary(
            'Interests',
            state.preferences['interests'] as List<String>? ?? [],
            Icons.favorite,
            AppColors.dubaiCoral,
          ),
          
          const SizedBox(height: 12),
          
          // Locations preview
          _buildPreferenceSummary(
            'Locations',
            state.preferences['preferredLocations'] as List<String>? ?? [],
            Icons.location_on,
            AppColors.dubaiTeal,
          ),
          
          const SizedBox(height: 12),
          
          // Budget preview
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.dubaiGold.withOpacity(0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.attach_money,
                  size: 16,
                  color: AppColors.dubaiGold,
                ),
              ),
              
              const SizedBox(width: 12),
              
              Text(
                'Budget: AED ${state.preferences['minPrice']?.toInt() ?? 0} - ${state.preferences['maxPrice']?.toInt() ?? 500}',
                style: GoogleFonts.inter(
                  fontSize: 14,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildAvatarStack(FamilyMember member, int index) {
    // Using Dicebear Avatars API for beautiful, diverse avatars
    final avatarUrl = 'https://api.dicebear.com/7.x/avataaars/svg?seed=${member.avatarSeed ?? member.name}';
    
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: AppColors.dubaiTeal.withOpacity(0.1),
        shape: BoxShape.circle,
        border: Border.all(
          color: Colors.white,
          width: 2,
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Image.network(
          avatarUrl,
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) {
            return CircleAvatar(
              backgroundColor: AppColors.dubaiTeal,
              child: Text(
                member.name.isNotEmpty ? member.name[0].toUpperCase() : '?',
                style: const TextStyle(color: Colors.white),
              ),
            );
          },
        ),
      ),
    );
  }
  
  Widget _buildPreferenceSummary(
    String title,
    List<String> items,
    IconData icon,
    Color color,
  ) {
    if (items.isEmpty) {
      return const SizedBox();
    }
    
    final displayItems = items.length > 3
        ? items.sublist(0, 3)
        : items;
    
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            shape: BoxShape.circle,
          ),
          child: Icon(
            icon,
            size: 16,
            color: color,
          ),
        ),
        
        const SizedBox(width: 12),
        
        Expanded(
          child: RichText(
            text: TextSpan(
              style: GoogleFonts.inter(
                fontSize: 14,
                color: AppColors.textPrimary,
              ),
              children: [
                TextSpan(
                  text: '$title: ',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                TextSpan(
                  text: displayItems.join(', ') + (items.length > 3 ? '...' : ''),
                ),
              ],
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}
```

## 4. User Profile Page Implementation

```dart
// features/profile/profile_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({Key? key}) : super(key: key);
  
  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen>
    with TickerProviderStateMixin {
  late TabController _tabController;
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }
  
  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    final onboardingState = ref.watch(onboardingProvider);
    final user = ref.watch(authProvider).user;
    
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          // Profile header
          _buildProfileHeader(user, onboardingState),
          
          // Tab bar
          SliverPersistentHeader(
            pinned: true,
            delegate: _StickyTabBarDelegate(
              TabBar(
                controller: _tabController,
                labelColor: AppColors.dubaiTeal,
                unselectedLabelColor: AppColors.textSecondary