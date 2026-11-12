(function () {
    'use strict';

    // Cart quantity controls submit automatically so totals stay current.
    document.querySelectorAll('[data-qty-form]').forEach(function (form) {
        var input = form.querySelector('.vw-qty-input');
        if (!input) {
            return;
        }
        form.querySelectorAll('[data-qty-step]').forEach(function (button) {
            button.addEventListener('click', function () {
                var step = parseInt(button.getAttribute('data-qty-step'), 10) || 0;
                var min = parseInt(input.getAttribute('min'), 10) || 1;
                var max = parseInt(input.getAttribute('max'), 10) || 999;
                var value = (parseInt(input.value, 10) || min) + step;
                value = Math.max(min, Math.min(max, value));
                input.value = value;
                form.submit();
            });
        });
        input.addEventListener('change', function () {
            form.submit();
        });
    });

    // Product detail size/colour selector.
    var variantRoot = document.querySelector('[data-variant-root]');
    var variantDataNode = document.getElementById('variant-data');
    if (variantRoot && variantDataNode) {
        var variants = [];
        try {
            variants = JSON.parse(variantDataNode.textContent || '[]');
        } catch (error) {
            variants = [];
        }
        var sizeWrap = document.getElementById('size-options');
        var colorWrap = document.getElementById('color-options');
        var hiddenInput = document.getElementById('variant-id');
        var stockLine = document.getElementById('variant-stock');
        var addButton = document.getElementById('add-to-cart-btn');
        var qtyInput = document.getElementById('qty-input');
        var selectedSize = null;
        var selectedColor = null;

        var unique = function (values) {
            return values.filter(function (item, index) {
                return values.indexOf(item) === index;
            });
        };
        var sizes = unique(variants.map(function (variant) { return variant.size; }));
        var colors = unique(variants.map(function (variant) { return variant.color; }));
        var colorHex = {};
        variants.forEach(function (variant) { colorHex[variant.color] = variant.hex; });

        var variantFor = function (size, color) {
            return variants.find(function (variant) {
                return variant.size === size && variant.color === color;
            });
        };

        var colorsForSize = function (size) {
            return colors.filter(function (color) {
                return Boolean(variantFor(size, color));
            });
        };

        var updateState = function () {
            var variant = variantFor(selectedSize, selectedColor);
            if (!variant) {
                hiddenInput.value = '';
                if (stockLine) {
                    stockLine.className = 'vw-stock-line vw-stock-out';
                    stockLine.textContent = 'Select a size and colour';
                }
                if (addButton) {
                    addButton.disabled = true;
                }
                return;
            }
            hiddenInput.value = variant.id;
            if (qtyInput) {
                var max = Math.min(Math.max(variant.stock, 1), 10);
                qtyInput.max = String(max);
                if (parseInt(qtyInput.value, 10) > max) {
                    qtyInput.value = String(max);
                }
            }
            if (stockLine) {
                if (variant.stock <= 0) {
                    stockLine.className = 'vw-stock-line vw-stock-out';
                    stockLine.textContent = 'Out of stock in this combination';
                } else if (variant.stock <= 5) {
                    stockLine.className = 'vw-stock-line vw-stock-low';
                    stockLine.textContent = 'Only ' + variant.stock + ' left in stock';
                } else {
                    stockLine.className = 'vw-stock-line vw-stock-in';
                    stockLine.textContent = 'In stock — ready to ship';
                }
            }
            if (addButton) {
                addButton.disabled = variant.stock <= 0;
                addButton.textContent = variant.stock <= 0 ? 'Out of stock' : 'Add to cart';
            }
        };

        var renderColors = function () {
            if (!colorWrap) {
                return;
            }
            colorWrap.innerHTML = '';
            colorsForSize(selectedSize).forEach(function (color) {
                var variant = variantFor(selectedSize, color);
                var button = document.createElement('button');
                button.type = 'button';
                button.className = 'vw-variant-btn vw-color-btn';
                button.setAttribute('data-color', color);
                if (variant && variant.stock <= 0) {
                    button.classList.add('is-disabled');
                }
                if (color === selectedColor) {
                    button.classList.add('is-selected');
                }
                var dot = document.createElement('span');
                dot.className = 'vw-color-dot';
                dot.style.background = colorHex[color] || '#000';
                button.appendChild(dot);
                button.appendChild(document.createTextNode(color));
                button.addEventListener('click', function () {
                    if (variant && variant.stock <= 0) {
                        return;
                    }
                    selectedColor = color;
                    renderColors();
                    updateState();
                });
                colorWrap.appendChild(button);
            });
        };

        var renderSizes = function () {
            if (!sizeWrap) {
                return;
            }
            sizeWrap.innerHTML = '';
            sizes.forEach(function (size) {
                var hasStock = variants.some(function (variant) {
                    return variant.size === size && variant.stock > 0;
                });
                var button = document.createElement('button');
                button.type = 'button';
                button.className = 'vw-variant-btn';
                button.setAttribute('data-size', size);
                button.textContent = size;
                if (!hasStock) {
                    button.classList.add('is-disabled');
                }
                if (size === selectedSize) {
                    button.classList.add('is-selected');
                }
                button.addEventListener('click', function () {
                    if (!hasStock) {
                        return;
                    }
                    selectedSize = size;
                    var availableColors = colorsForSize(size);
                    if (availableColors.indexOf(selectedColor) === -1) {
                        var firstInStock = availableColors.find(function (color) {
                            var variant = variantFor(size, color);
                            return variant && variant.stock > 0;
                        });
                        selectedColor = firstInStock || availableColors[0] || null;
                    }
                    renderSizes();
                    renderColors();
                    updateState();
                });
                sizeWrap.appendChild(button);
            });
        };

        var initial = variants.find(function (variant) { return variant.stock > 0; }) || variants[0];
        if (initial) {
            selectedSize = initial.size;
            selectedColor = initial.color;
        }
        renderSizes();
        renderColors();
        updateState();

        var form = variantRoot.closest('form');
        if (form) {
            form.addEventListener('submit', function (event) {
                if (!hiddenInput.value) {
                    event.preventDefault();
                    if (stockLine) {
                        stockLine.className = 'vw-stock-line vw-stock-out';
                        stockLine.textContent = 'Please select an available size and colour.';
                    }
                }
            });
        }
    }

    // Product gallery thumbnails.
    var mainImage = document.getElementById('gallery-main-image');
    document.querySelectorAll('[data-gallery-src]').forEach(function (thumb) {
        thumb.addEventListener('click', function () {
            if (!mainImage) {
                return;
            }
            mainImage.src = thumb.getAttribute('data-gallery-src');
            document.querySelectorAll('[data-gallery-src]').forEach(function (item) {
                item.classList.remove('is-active');
            });
            thumb.classList.add('is-active');
        });
    });

    // Shop sort select submits without an extra click.
    document.querySelectorAll('[data-auto-submit]').forEach(function (element) {
        element.addEventListener('change', function () {
            if (element.form) {
                element.form.submit();
            }
        });
    });

    // Checkout: reveal the new address form when requested.
    var addressRadios = document.querySelectorAll('input[name="address_id"]');
    var newAddressBlock = document.getElementById('new-address-fields');
    var syncAddressBlock = function () {
        if (!newAddressBlock) {
            return;
        }
        var selected = document.querySelector('input[name="address_id"]:checked');
        newAddressBlock.hidden = Boolean(selected && selected.value !== 'new');
    };
    addressRadios.forEach(function (radio) {
        radio.addEventListener('change', syncAddressBlock);
    });
    syncAddressBlock();
})();
