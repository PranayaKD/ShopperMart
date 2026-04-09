/**
 * Boneyard JS - Vanilla DOM Wrapper
 * Inspired by 0xGF/boneyard
 * Dynamically wraps designated UI elements to create structure-preserving skeleton loaders.
 * Perfect for images and data sections that load progressively.
 */

document.addEventListener('DOMContentLoaded', () => {
    class Boneyard {
        static init() {
            const bones = document.querySelectorAll('[data-boneyard]');
            
            bones.forEach(element => {
                // Check if it's an image
                const isImage = element.tagName.toLowerCase() === 'img';
                
                // Skip if image is already loaded via fast cache
                if (isImage && element.complete && element.naturalHeight !== 0) {
                    element.style.opacity = '1';
                    return;
                }

                this.wrapElement(element, isImage);
            });
        }

        static wrapElement(element, isImage) {
            // Create the wrapper mimicking the element layout
            const wrapper = document.createElement('div');
            
            const boneType = element.getAttribute('data-boneyard') || 'pulse'; // 'pulse' or 'shimmer'
            const boneClasses = element.getAttribute('data-boneyard-class') || 'w-full h-full';
            const bgClass = element.getAttribute('data-boneyard-bg') || 'bg-black/10';
            
            wrapper.classList.add('relative', 'overflow-hidden', 'boneyard-wrapper');
            
            if (boneClasses) {
                boneClasses.split(' ').forEach(cls => {
                    if (cls.trim()) wrapper.classList.add(cls);
                });
            }

            // Insert wrapper exactly where the element is
            element.parentNode.insertBefore(wrapper, element);
            
            // Hide element temporarily while loading
            element.style.opacity = '0';
            
            // Move item inside wrapper
            wrapper.appendChild(element);

            // Create visible skeleton layer
            const bone = document.createElement('div');
            bone.className = `absolute inset-0 z-10 ${bgClass} boneyard-bone pointer-events-none`;
            
            // Add animation type
            if (boneType === 'shimmer') {
                bone.classList.add('boneyard-theme-shimmer'); 
            } else {
                bone.classList.add('animate-pulse'); // Tailwind default
            }

            wrapper.appendChild(bone);
            
            // Register unwrapping handlers
            if (isImage) {
                element.addEventListener('load', () => this.unwrap(wrapper, bone));
                element.addEventListener('error', () => this.unwrap(wrapper, bone));
                
                // Fallback catch for quick completions
                if (element.complete && element.naturalHeight !== 0) {
                     this.unwrap(wrapper, bone);
                }
            } else {
                // If it's a generic text node, wait for mock load (or trigger externally)
                const delay = parseInt(element.getAttribute('data-boneyard-delay')) || 1500;
                setTimeout(() => this.unwrap(wrapper, bone), delay);
            }
        }

        static unwrap(wrapper, bone) {
            if (!bone.parentNode) return; // Prevent double firing
            
            // Fade out the skeleton
            bone.style.transition = 'opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            bone.style.opacity = '0';
            
            setTimeout(() => {
                const element = wrapper.querySelector('[data-boneyard]');
                if (element) {
                    element.style.transition = 'opacity 0.5s cubic-bezier(0.0, 0, 0.2, 1)';
                    element.style.opacity = '1';
                }
                bone.remove();
                
                // Attempt to remove wrapper DOM debt safely
                if (element && wrapper.parentNode) {
                    // Extract element and place it before the wrapper
                    wrapper.parentNode.insertBefore(element, wrapper);
                    wrapper.remove(); // Clean up
                }
            }, 400);
        }
    }

    // Attach globally
    window.BoneyardRenderer = Boneyard;
    Boneyard.init();
});
