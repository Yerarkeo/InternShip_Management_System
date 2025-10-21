// Main JavaScript functionality for Internship Management System
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    initializeTooltips();
    initializeFormValidation();
    initializeModalHandlers();
    initializeProgressBars();
}

// Tooltip functionality
function initializeTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(tooltip => {
        tooltip.addEventListener('mouseenter', showTooltip);
        tooltip.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(event) {
    const tooltipText = event.target.getAttribute('data-tooltip');
    if (!tooltipText) return;

    const tooltip = document.createElement('div');
    tooltip.className = 'fixed z-50 px-3 py-2 text-sm text-white bg-gray-900 rounded-lg shadow-lg max-w-xs';
    tooltip.textContent = tooltipText;
    tooltip.id = 'dynamic-tooltip';
    tooltip.style.opacity = '0';
    tooltip.style.transition = 'opacity 0.2s';
    
    document.body.appendChild(tooltip);
    
    const rect = event.target.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    
    // Position tooltip above the element
    let top = rect.top - tooltipRect.height - 8;
    let left = rect.left + (rect.width - tooltipRect.width) / 2;
    
    // Adjust if tooltip goes off screen
    if (left < 8) left = 8;
    if (left + tooltipRect.width > window.innerWidth - 8) {
        left = window.innerWidth - tooltipRect.width - 8;
    }
    if (top < 8) top = rect.bottom + 8;
    
    tooltip.style.top = top + 'px';
    tooltip.style.left = left + 'px';
    
    setTimeout(() => {
        tooltip.style.opacity = '1';
    }, 10);
}

function hideTooltip() {
    const tooltip = document.getElementById('dynamic-tooltip');
    if (tooltip) {
        tooltip.style.opacity = '0';
        setTimeout(() => {
            if (tooltip.parentNode) {
                tooltip.parentNode.removeChild(tooltip);
            }
        }, 200);
    }
}

// Form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('form[needs-validation]');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!validateForm(this)) {
                event.preventDefault();
                event.stopPropagation();
            }
            this.classList.add('was-validated');
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            showInputError(input, 'This field is required');
            isValid = false;
        } else {
            clearInputError(input);
        }
        
        // Email validation
        if (input.type === 'email' && input.value.trim()) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(input.value)) {
                showInputError(input, 'Please enter a valid email address');
                isValid = false;
            }
        }
        
        // Password strength validation
        if (input.type === 'password' && input.value.trim()) {
            if (input.value.length < 6) {
                showInputError(input, 'Password must be at least 6 characters long');
                isValid = false;
            }
        }
    });
    
    return isValid;
}

function showInputError(input, message) {
    clearInputError(input);
    input.classList.add('border-red-500');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'text-red-500 text-sm mt-1';
    errorDiv.textContent = message;
    input.parentNode.appendChild(errorDiv);
}

function clearInputError(input) {
    input.classList.remove('border-red-500');
    const existingError = input.parentNode.querySelector('.text-red-500');
    if (existingError) {
        existingError.remove();
    }
}

// Modal handlers
function initializeModalHandlers() {
    // Close modals when clicking outside
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal-overlay')) {
            hideAllModals();
        }
    });
    
    // Close modals with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            hideAllModals();
        }
    });
}

function hideAllModals() {
    const modals = document.querySelectorAll('.modal-overlay');
    modals.forEach(modal => {
        modal.classList.add('hidden');
    });
}

// Progress bar animation
function initializeProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const progress = bar.getAttribute('data-progress') || bar.style.width.replace('%', '');
        animateProgressBar(bar, progress);
    });
}

function animateProgressBar(bar, targetProgress) {
    let currentProgress = 0;
    const duration = 1000; // 1 second
    const increment = targetProgress / (duration / 16); // 60fps
    
    function updateProgress() {
        if (currentProgress < targetProgress) {
            currentProgress += increment;
            if (currentProgress > targetProgress) currentProgress = targetProgress;
            
            bar.style.width = currentProgress + '%';
            bar.setAttribute('aria-valuenow', currentProgress);
            
            // Update color based on progress
            if (currentProgress < 30) {
                bar.className = bar.className.replace(/(bg-)(\S+)/, '$1red-500');
            } else if (currentProgress < 70) {
                bar.className = bar.className.replace(/(bg-)(\S+)/, '$1yellow-500');
            } else {
                bar.className = bar.className.replace(/(bg-)(\S+)/, '$1green-500');
            }
            
            requestAnimationFrame(updateProgress);
        }
    }
    
    updateProgress();
}

// API helper functions
async function apiCall(endpoint, options = {}) {
    const token = getCookie('access_token');
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': token })
        },
        credentials: 'same-origin'
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(endpoint, mergedOptions);
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Network error' }));
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// Notification system
function showNotification(message, type = 'info', duration = 5000) {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    });
    
    const notification = document.createElement('div');
    const typeClasses = {
        success: 'bg-green-500 border-green-600',
        error: 'bg-red-500 border-red-600',
        warning: 'bg-yellow-500 border-yellow-600',
        info: 'bg-blue-500 border-blue-600'
    };
    
    notification.className = `notification fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 text-white border-l-4 ${
        typeClasses[type] || typeClasses.info
    } transform transition-transform duration-300 translate-x-full`;
    
    notification.innerHTML = `
        <div class="flex items-center">
            <i class="fas ${getNotificationIcon(type)} mr-3"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-white hover:text-gray-200">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 10);
    
    // Auto remove after duration
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentNode) {
                notification.classList.add('translate-x-full');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        }, duration);
    }
    
    return notification;
}

function getNotificationIcon(type) {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    return icons[type] || icons.info;
}

// Form handling utilities
function serializeForm(form) {
    const formData = new FormData(form);
    const data = {};
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    return data;
}

function handleFormSubmit(form, endpoint, options = {}) {
    form.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton.innerHTML;
        
        // Show loading state
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Loading...';
        
        try {
            const data = serializeForm(form);
            const response = await apiCall(endpoint, {
                method: 'POST',
                body: JSON.stringify(data),
                ...options
            });
            
            showNotification(options.successMessage || 'Operation completed successfully!', 'success');
            
            if (options.onSuccess) {
                options.onSuccess(response);
            } else if (options.redirect) {
                setTimeout(() => {
                    window.location.href = options.redirect;
                }, 1000);
            }
            
        } catch (error) {
            // Error handling is done in apiCall
        } finally {
            // Restore button state
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        }
    });
}

// Date utilities
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Search and filter functionality
function initializeSearch(inputSelector, containerSelector, itemSelector) {
    const searchInput = document.querySelector(inputSelector);
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const items = document.querySelectorAll(containerSelector + ' ' + itemSelector);
        
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(searchTerm)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

// Confirmation dialog
function confirmAction(message, callback) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center';
    modal.innerHTML = `
        <div class="bg-white rounded-lg shadow-xl p-6 max-w-sm mx-auto">
            <h3 class="text-lg font-medium text-gray-900 mb-4">Confirm Action</h3>
            <p class="text-gray-600 mb-6">${message}</p>
            <div class="flex justify-end space-x-3">
                <button onclick="this.closest('.fixed').remove()" class="px-4 py-2 text-gray-600 hover:text-gray-800 transition">
                    Cancel
                </button>
                <button onclick="this.closest('.fixed').remove(); callback()" 
                        class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition">
                    Confirm
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Store callback in global scope temporarily
    window.confirmCallback = callback;
}

// Export functions for global use
window.showNotification = showNotification;
window.confirmAction = confirmAction;
window.formatDate = formatDate;
window.formatDateTime = formatDateTime;
window.apiCall = apiCall;